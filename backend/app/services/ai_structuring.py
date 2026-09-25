"""AI transcript structuring and lecture-grounded Q&A service.

Transforms raw speech-to-text transcript chunks into clean, structured
educational notes by removing filler words, preserving technical terms,
identifying the lecture topic, extracting key points, detecting important concepts,
identifying technical terms, extracting numbers/formulas, and attributing speakers.

Also provides lecture-grounded Q&A where the current lecture session is the
strict source of truth, preventing hallucinations.
"""

from __future__ import annotations

import json
import os
import re
from abc import ABC, abstractmethod
from typing import Any

import httpx

SYSTEM_PROMPT = """You are an educational assistant that transforms raw speech-to-text lecture transcripts into clean, readable educational notes.

Follow these strict rules:
1. Remove filler words such as "um", "uh", "like", "basically", "you know", "sort of", "kind of", "right?", "okay" when they do not add meaning.
2. Correct obvious speech-to-text noise and transcription errors where safe.
3. Preserve the exact meaning and tone of the teacher's statement.
4. Break long speech into clear, readable paragraphs or sections.
5. Identify the primary educational topic being taught.
6. Extract concise, bulleted key points summarizing the core ideas.
7. IMPORTANT CONCEPTS:
   - Identify the major educational concepts, theories, principles, or frameworks being taught.
   - Prefer meaningful educational concepts students should remember (e.g. "Supervised Learning", "Training Data", "Input-Output Mapping", "Newton's First Law").
8. TECHNICAL TERMS:
   - Identify domain-specific technical terminology, vocabulary, algorithms, methods, technologies, scientific/engineering terms, and mathematical/statistical words (e.g. "labelled data", "classification", "regression", "model", "feature").
9. NUMBERS:
   - Extract educationally relevant numerical information, measurements, percentages, constants, dates/years, quantities, and ratios with their associated units (e.g. "95%", "10 kg", "25\u00b0C", "9.81 m/s\u00b2", "2026", "3.14", "10 students").
   - Do NOT blindly extract meaningless counter numbers.
10. FORMULAS:
   - Detect mathematical, scientific, and technical equations or relationships mentioned or spoken in the lecture.
   - Represent formulas cleanly using standard mathematical notation (e.g. "F = ma", "A = \u03c0r\u00b2", "y = mx + c", "V = IR", "Accuracy = Correct Predictions / Total Predictions").
   - Do NOT hallucinate formulas. If no formula is spoken, return an empty list [].
11. SPEAKER ATTRIBUTION:
   - Attribute transcript segments to speakers using available context.
   - The primary lecture delivery comes from the teacher: assign "Teacher".
   - If explicit conversational markers are present (e.g. "Teacher:", "Student:"), preserve and attribute accordingly.
   - If speaker origin is ambiguous or cannot be verified, assign "Unknown".
   - Allowed speaker values are STRICTLY: "Teacher", "Student", or "Unknown".
   - NEVER guess or invent speaker identity based on conversational style alone.
12. Keep all technical terms, formulas, numbers, and domain terminology intact.
13. NEVER invent information that was not present in the transcript.
14. CURRENT TOPIC & TOPIC HISTORY:
   - Dynamically identify the current active topic being taught. Distinguish between previous topics and topic transitions (e.g. "Today we will learn supervised learning", "Now let's move to classification").
   - "topic" must hold the CURRENT active topic.
   - "topic_history" must contain the chronological list of topics covered so far, e.g. [{"topic": "Supervised Learning", "timestamp": null}, {"topic": "Classification", "timestamp": null}].
   - Do NOT invent timestamps if not present in the transcript (use null).
15. IMPORTANT POINTS:
   - Identify statements explicitly emphasized by the lecturer (e.g. "Remember that...", "An important point is...", "Note that...", "The key difference is...", "Keep in mind...", "This is important...", "Most importantly...", "Do not forget...").
   - Do NOT simply duplicate every general key point; capture explicitly emphasized educational takeaways.
16. DEFINITIONS:
   - Extract clear, explicit definitions spoken in the lecture (e.g. "An algorithm is a step-by-step procedure for solving a problem." -> term: "Algorithm", definition: "A step-by-step procedure for solving a problem.").
   - Do NOT hallucinate definitions from outside knowledge.
17. EXAMPLES:
   - Extract concrete examples mentioned in the lecture (e.g. "For example, spam detection is a classification problem." -> concept: "Classification", example: "Spam detection").
   - Only include examples actually mentioned in the lecture.
18. IMPORTANT MOMENTS:
   - Extract review-worthy moments categorized by type: "definition", "formula", "important_point", "example", "concept", "warning".
   - Each moment must follow: {"type": "definition", "content": "...", "timestamp": null}. Do NOT invent timestamps.

You must respond with ONLY a valid JSON object matching this schema:
{
  "clean_text": "Cleaned, structured lecture text with fillers removed and clear formatting",
  "topic": "Current active topic title",
  "key_points": [
    "Key takeaway or point 1",
    "Key takeaway or point 2"
  ],
  "concepts": [
    "Major Concept 1",
    "Major Concept 2"
  ],
  "technical_terms": [
    "technical term 1",
    "technical term 2"
  ],
  "numbers": [
    "95%",
    "10 kg"
  ],
  "formulas": [
    "F = ma"
  ],
  "speaker_segments": [
    {
      "speaker": "Teacher",
      "text": "Segment text here",
      "timestamp": null
    }
  ],
  "topic_history": [
    {
      "topic": "Previous or initial topic",
      "timestamp": null
    },
    {
      "topic": "Current topic",
      "timestamp": null
    }
  ],
  "important_points": [
    "Emphasized educational statement"
  ],
  "definitions": [
    {
      "term": "Term",
      "definition": "Explicit definition"
    }
  ],
  "examples": [
    {
      "concept": "Concept Name",
      "example": "Concrete example mentioned"
    }
  ],
  "important_moments": [
    {
      "type": "definition",
      "content": "Algorithm: A step-by-step procedure...",
      "timestamp": null
    }
  ]
}
"""

QA_SYSTEM_PROMPT = """You are an educational assistant answering student questions about a specific lecture in a multi-turn conversation.

CRITICAL RULES:
1. Use ONLY the supplied lecture content as the source of truth.
2. Maintain strict grounding in the CURRENT lecture session. Do NOT use outside/general knowledge or introduce external facts.
3. If the answer cannot be found or reasonably derived from the lecture content, you must explicitly state: "This was not covered in the current lecture."
4. Do NOT invent or hallucinate facts, definitions, formulas, examples, numbers, or concepts not supported by the lecture.
5. In multi-turn conversation, understand that follow-up questions (using pronouns such as "that", "this", "it", "the formula", "the second one", etc., or requests like "explain simply", "give an example") refer to the prior conversation history and previously discussed lecture topics.
6. If the student asks to explain something simply, simplify the concept using ONLY the facts provided in the lecture.
7. If the student asks for an example, use ONLY examples mentioned in the lecture. If none was mentioned, explicitly state that an example was not given in the lecture.
8. Include the exact relevant sentence or snippet from the lecture in the "sources" list.
9. If the question was not covered, return "lecture_grounded": false and "sources": []. If answered from the lecture, return "lecture_grounded": true.

You must respond with ONLY a valid JSON object matching this schema:
{
  "question": "The question asked",
  "answer": "Concise answer strictly derived from lecture content",
  "sources": [
    "Relevant lecture snippet or quote"
  ],
  "lecture_grounded": true
}
"""


class AIStructuringError(Exception):
    """Raised when structuring transcript or answering questions fails."""


class AIProvider(ABC):
    """Abstract interface for AI structuring and Q&A providers."""

    @abstractmethod
    async def structure_transcript(self, text: str) -> dict[str, Any]:
        """Structure raw transcript text into clean_text, topic, key_points, concepts, technical_terms, numbers, formulas, and speaker_segments."""

    @abstractmethod
    async def answer_question(
        self,
        question: str,
        lecture_text: str,
        conversation_history: list[dict[str, Any]] | None = None,
        lecture_structured_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Answer a student's question grounded strictly in the provided lecture content."""


class HeuristicAIProvider(AIProvider):
    """Rule-based local fallback provider.

    Used when external LLM API keys are not provided or for offline/local operation.
    Removes common verbal fillers, standardizes sentence casing and punctuation,
    extracts representative key points, educational concepts, domain terms, numbers,
    formulas, and attributes speakers. Also performs deterministic grounded Q&A.
    """

    FILLER_WORDS = [
        r"\bum+\b",
        r"\buh+\b",
        r"\bah+\b",
        r"\ber+\b",
        r"\byou know\b",
        r"\bkind of\b",
        r"\bsort of\b",
        r"\bbasically\b",
        r"\bactually\b",
        r"\blike\b",
        r"\bright\?",
        r"\bi mean\b",
    ]

    COMMON_TECHNICAL_KEYWORDS = [
        "supervised learning",
        "unsupervised learning",
        "reinforcement learning",
        "machine learning",
        "deep learning",
        "neural network",
        "gradient descent",
        "classification",
        "regression",
        "clustering",
        "algorithm",
        "training data",
        "test data",
        "feature",
        "label",
        "parameter",
        "hyperparameter",
        "overfitting",
        "underfitting",
        "loss function",
        "accuracy",
        "precision",
        "recall",
        "f1 score",
        "dataset",
        "model",
        "database",
        "sql",
        "nosql",
        "relational",
        "foreign key",
        "primary key",
        "index",
        "transaction",
        "acid",
        "normalization",
        "fastapi",
        "python",
        "javascript",
        "sqlite",
        "latency",
        "bandwidth",
        "throughput",
        "cpu",
        "memory",
        "acceleration",
        "velocity",
        "gravity",
        "frequency",
        "resistance",
        "voltage",
        "current",
        "radius",
        "diameter",
        "circumference",
        "area",
        "volume",
    ]

    FORMULA_PATTERNS = [
        (r"\b(?:f\s*=\s*m\s*a|force\s+equals\s+mass\s+times\s+acceleration)\b", "F = ma"),
        (r"\b(?:a\s*=\s*(?:\u03c0|pi)\s*r\s*(?:\^2|\u00b2|squared)|area\s+equals\s+pi\s+r\s+squared|area\s+of\s+a\s+circle\s+is\s+pi\s+r\s+squared)\b", "A = \u03c0r\u00b2"),
        (r"\b(?:v\s*=\s*i\s*r|v\s+equals\s+i\s+r|voltage\s+equals\s+current\s+times\s+resistance)\b", "V = IR"),
        (r"\b(?:e\s*=\s*m\s*c\s*(?:\^2|\u00b2|squared)|e\s+equals\s+m\s+c\s+squared)\b", "E = mc\u00b2"),
        (r"\b(?:y\s*=\s*m\s*x\s*\+\s*c|y\s*=\s*m\s*x\s*\+\s*b)\b", "y = mx + c"),
        (r"\b(?:a\s*(?:\^2|\u00b2)\s*\+\s*b\s*(?:\^2|\u00b2)\s*=\s*c\s*(?:\^2|\u00b2)|pythagorean\s+theorem)\b", "a\u00b2 + b\u00b2 = c\u00b2"),
        (r"\b(?:s\s*=\s*d\s*/\s*t|speed\s+equals\s+distance\s+over\s+time)\b", "Speed = Distance / Time"),
        (r"\b(?:accuracy\s*=\s*correct\s*/\s*total|accuracy\s+equals\s+correct\s+predictions\s+divided\s+by\s+total)\b", "Accuracy = Correct / Total"),
    ]

    async def structure_transcript(self, text: str) -> dict[str, Any]:
        cleaned = self._clean_text(text)
        topic, topic_history = self._infer_topic_and_history(cleaned)
        key_points = self._extract_key_points(cleaned)
        concepts = self._extract_concepts(cleaned, topic)
        technical_terms = self._extract_technical_terms(cleaned)
        numbers = self._extract_numbers(cleaned)
        formulas = self._extract_formulas(text + " " + cleaned)
        speaker_segments = self._attribute_speakers(text, cleaned)
        important_points = self._extract_important_points(cleaned)
        definitions = self._extract_definitions(cleaned)
        examples = self._extract_examples(cleaned, topic)
        important_moments = self._extract_important_moments(
            definitions, formulas, important_points, examples, cleaned
        )

        return {
            "clean_text": cleaned,
            "topic": topic,
            "key_points": key_points,
            "concepts": concepts,
            "technical_terms": technical_terms,
            "numbers": numbers,
            "formulas": formulas,
            "speaker_segments": speaker_segments,
            "topic_history": topic_history,
            "important_points": important_points,
            "definitions": definitions,
            "examples": examples,
            "important_moments": important_moments,
        }

    def _extract_subject_from_history(self, history: list[dict[str, Any]]) -> str | None:
        if not history:
            return None
        for msg in reversed(history):
            content = msg.get("content", "")
            content_lower = content.lower()
            for kw in self.COMMON_TECHNICAL_KEYWORDS:
                if re.search(r"\b" + re.escape(kw) + r"\b", content_lower):
                    return kw
            m = re.search(r"\b(?:what is|what are|explain|about|define)\s+([a-zA-Z0-9\s\-]+?)(?=[?.!]|$)", content, re.IGNORECASE)
            if m:
                cand = m.group(1).strip()
                cand_words = [w for w in cand.split() if w.lower() not in {"the", "a", "an", "that", "it", "this", "simply", "to"}]
                if cand_words:
                    return " ".join(cand_words)
        return None

    async def answer_question(
        self,
        question: str,
        lecture_text: str,
        conversation_history: list[dict[str, Any]] | None = None,
        lecture_structured_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        q_clean = question.strip()
        if not q_clean:
            raise ValueError("Question cannot be empty.")

        lec_clean = lecture_text.strip()
        if not lec_clean:
            return {
                "question": q_clean,
                "answer": "The lecture does not contain enough content to answer this yet.",
                "sources": [],
                "lecture_grounded": False,
            }

        q_lower = q_clean.lower()

        # Reject explicitly unmentioned / outside requests
        if any(p in q_lower for p in ["didn't mention", "did not mention", "outside the lecture", "outside of the lecture", "not in the lecture", "not covered in class"]):
            return {
                "question": q_clean,
                "answer": "The current lecture does not provide enough information for that.",
                "sources": [],
                "lecture_grounded": False,
            }

        # Split lecture into sentences
        sentences = [
            s.strip()
            for s in re.split(r"(?<=[.!?])\s+|\n+", lec_clean)
            if s.strip()
        ]

        recent_history = conversation_history[-10:] if conversation_history else []
        previous_subject = self._extract_subject_from_history(recent_history)
        last_assistant_msg = next((m.get("content", "") for m in reversed(recent_history) if m.get("role") == "assistant"), "")

        is_simplify = any(w in q_lower for w in ["simply", "simple terms", "simplify", "easier", "in simple terms"])
        is_example = any(w in q_lower for w in ["example", "instance", "sample"])

        # 1. Ordinal reference follow-up (e.g. "Explain the second one" or "What was the first topic?")
        ordinal_map = {
            "first": 0, "second": 1, "third": 2, "fourth": 3,
            "1st": 0, "2nd": 1, "3rd": 2, "4th": 3,
        }
        for ord_word, ord_idx in ordinal_map.items():
            if re.search(r"\b" + ord_word + r"\b", q_lower):
                items = []
                if last_assistant_msg:
                    m_list = re.findall(r"\b(?:[A-Z][a-zA-Z0-9_\-\s]{2,25})(?:,|\band\b|$)", last_assistant_msg)
                    if len(m_list) > ord_idx:
                        items = [re.sub(r"^(?:and|,)\s*", "", it).strip() for it in m_list if it.strip()]
                if not items:
                    for s in sentences:
                        if any(t in s.lower() for t in ["two topics", "three topics", "topics:", "covered:", "includes:"]):
                            parts = re.split(r"[:,]\s*|\band\b", s)
                            items = [p.strip() for p in parts[1:] if p.strip()]
                            break

                if items and len(items) > ord_idx:
                    target_concept = items[ord_idx]
                    for s in sentences:
                        if target_concept.lower() in s.lower() and len(s) > len(target_concept) + 5:
                            clean_s = re.sub(r"^(?:teacher|student|unknown):\s*", "", s, flags=re.IGNORECASE).strip()
                            return {
                                "question": q_clean,
                                "answer": clean_s,
                                "sources": [clean_s],
                                "lecture_grounded": True,
                            }
                    return {
                        "question": q_clean,
                        "answer": f"The lecture covered {target_concept}.",
                        "sources": [s for s in sentences if target_concept.lower() in s.lower()][:1],
                        "lecture_grounded": True,
                    }

        # 2. Formula questions (e.g. "What is the formula?" or "What formula was mentioned?")
        is_formula_query = any(w in q_lower for w in ["formula", "equation", "law", "f = ma", "v = ir", "e = mc", "pythagor", "area", "speed"])
        if is_formula_query:
            detected_formulas = self._extract_formulas(lec_clean)
            if detected_formulas:
                matching_sentence = next(
                    (s for s in sentences if any(f.split("=")[0].strip().lower() in s.lower() or "formula" in s.lower() for f in detected_formulas)),
                    sentences[0],
                )
                formula_str = ", ".join(detected_formulas)
                return {
                    "question": q_clean,
                    "answer": f"The lecture mentioned the formula {formula_str}.",
                    "sources": [matching_sentence],
                    "lecture_grounded": True,
                }
            elif previous_subject:
                return {
                    "question": q_clean,
                    "answer": "This was not covered in the current lecture.",
                    "sources": [],
                    "lecture_grounded": False,
                }

        # 3. Example follow-up (e.g. "Give an example" or "Give me an example")
        if is_example:
            ex_sentences = [
                s for s in sentences
                if any(p in s.lower() for p in ["for example", "for instance", "such as", "an example of"])
            ]
            if ex_sentences:
                best_ex = None
                if previous_subject:
                    best_ex = next((s for s in ex_sentences if previous_subject.lower() in s.lower()), None)
                if not best_ex:
                    best_ex = ex_sentences[0]

                clean_ex = re.sub(r"^(?:teacher|student|unknown):\s*", "", best_ex, flags=re.IGNORECASE).strip()
                return {
                    "question": q_clean,
                    "answer": clean_ex,
                    "sources": [clean_ex],
                    "lecture_grounded": True,
                }
            elif previous_subject or "example" in q_lower:
                return {
                    "question": q_clean,
                    "answer": "This was not covered in the current lecture.",
                    "sources": [],
                    "lecture_grounded": False,
                }

        # 4. Number / measurement questions
        is_number_query = any(w in q_lower for w in ["number", "percentage", "accuracy", "temperature", "metric", "gravity", "measurement", "value", "how much", "how many", "score", "rate"])
        if is_number_query:
            numbers = self._extract_numbers(lec_clean)
            if numbers:
                for num in numbers:
                    num_base = num.split()[0].replace("%", "").replace("\u00b0c", "").replace("\u00b0C", "")
                    for s in sentences:
                        if num.lower() in s.lower() or num_base.lower() in s.lower():
                            return {
                                "question": q_clean,
                                "answer": f"According to the lecture, the relevant value is {num}.",
                                "sources": [s],
                                "lecture_grounded": True,
                            }

        # 5. Topic, Concept, or General Content questions
        stop_words = {
            "what", "is", "are", "the", "a", "an", "and", "or", "in", "on", "at", "to", "for", "of",
            "with", "did", "does", "do", "how", "why", "can", "you", "tell", "me", "about", "explain",
            "simply", "simple", "teacher", "mention", "lecture", "taught", "today", "study", "class",
            "use", "uses", "used", "using", "which", "who", "whom", "where", "when", "there", "their",
            "have", "has", "had", "having", "give", "gives", "given", "giving", "that", "this", "it",
            "one", "more", "much", "understand",
        }
        words = re.findall(r"[a-z0-9\u00b0\u00b2\u03c0]+", q_lower)
        keywords = [w for w in words if w not in stop_words and len(w) > 1]

        # Follow-up pronoun reference: borrow keywords from previous subject
        if not keywords and previous_subject:
            sub_words = re.findall(r"[a-z0-9]+", previous_subject.lower())
            keywords = [w for w in sub_words if w not in stop_words and len(w) > 1]

        best_sentence = None
        best_score = 0

        for s in sentences:
            clean_s = re.sub(r"^(?:teacher|student|unknown):\s*", "", s, flags=re.IGNORECASE).strip()
            clean_s_lower = clean_s.lower()

            score = 0
            kws_matched = 0
            for kw in keywords:
                if re.search(r"\b" + re.escape(kw) + r"\b", clean_s_lower):
                    score += 3
                    kws_matched += 1
                elif kw in clean_s_lower:
                    score += 1
                    kws_matched += 1

            if kws_matched > 0:
                if any(p in clean_s_lower for p in [" is ", " are ", " refers to ", " means ", " predict", " uses "]):
                    score += 1

            if len(keywords) >= 2 and kws_matched < 2 and score < 6:
                continue

            if score > best_score and kws_matched >= 1:
                best_score = score
                best_sentence = clean_s

        if best_sentence and best_score >= 2:
            answer_text = best_sentence
            if is_simplify:
                if "predicts" in answer_text.lower():
                    answer_text = re.sub(r"\bpredicts\b", "is used to predict", answer_text, flags=re.IGNORECASE)
                elif not answer_text.lower().startswith("in simple terms"):
                    answer_text = f"In simple terms, {answer_text[0].lower() + answer_text[1:]}"

            return {
                "question": q_clean,
                "answer": answer_text,
                "sources": [best_sentence],
                "lecture_grounded": True,
            }

        return {
            "question": q_clean,
            "answer": "This was not covered in the current lecture.",
            "sources": [],
            "lecture_grounded": False,
        }

    def _clean_text(self, text: str) -> str:
        cleaned = text.strip()
        for pattern in self.FILLER_WORDS:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

        cleaned = re.sub(r"\s+", " ", cleaned)
        cleaned = re.sub(r"\s+([.,!?;:])", r"\1", cleaned)

        sentences = re.split(r"(?<=[.!?])\s+", cleaned)
        formatted_sentences = []
        for s in sentences:
            s = s.strip()
            if not s:
                continue
            s = s[0].upper() + s[1:]
            if not s.endswith((".", "!", "?")):
                s += "."
            formatted_sentences.append(s)

        return " ".join(formatted_sentences)

    @staticmethod
    def _clean_topic_phrase(raw: str) -> str:
        cleaned = re.sub(
            r"^(?:the\s+concept\s+of|concept\s+of|the\s+topic\s+of|topic\s+of|the|a|an)\s+",
            "",
            raw.strip(),
            flags=re.IGNORECASE,
        )
        cleaned = re.sub(r"[.,!?;:]+$", "", cleaned).strip()
        cleaned = re.split(r"\s+(?:where|which|because|as|and\s+then)\b", cleaned, flags=re.IGNORECASE)[0]
        words = [w.capitalize() for w in cleaned.split() if w.lower() not in {"a", "an", "the", "in", "of", "and", "to", "for"}]
        words = words[:5]
        return " ".join(words) if words else cleaned.title()

    def _infer_topic_and_history(self, text: str) -> tuple[str, list[dict[str, Any]]]:
        topic_intro_patterns = [
            r"\btoday(?:\s+we\s+are|\s+we\s+will|\s+we'll|\s+we)\s+(?:going\s+to\s+)?(?:study|discuss|learn|focus\s+on|cover|explore)\s+(?:the\s+)?(?:concept\s+of\s+)?([^.,!?;]+)",
            r"\btoday's\s+lecture\s+is\s+about\s+([^.,!?;]+)",
            r"\bwe\s+are\s+covering\s+([^.,!?;]+)",
            r"\blet\s+us\s+discuss\s+([^.,!?;]+)",
            r"\bintroduction\s+to\s+([^.,!?;]+)",
            r"\bwelcome\s+to\s+(?:today's\s+lecture\s+on\s+)?([^.,!?;]+)",
        ]
        topic_transition_patterns = [
            r"(?:now\s+let's|now\s+we|let's|let\s+us)\s+move\s+(?:on\s+)?to\s+([^.,!?;]+)",
            r"(?:moving\s+on\s+to|turning\s+to)\s+([^.,!?;]+)",
            r"(?:next\s+we\s+will|next\s+we'll|next\s+we\s+are\s+going\s+to|next\s+let's)\s+(?:discuss|cover|study|look\s+at)\s+([^.,!?;]+)",
            r"(?:our\s+next\s+topic\s+is|next\s+topic\s+is|next\s+concept\s+is)\s+([^.,!?;]+)",
            r"(?:now\s+let's\s+discuss|now\s+we\s+discuss)\s+([^.,!?;]+)",
        ]

        found_mentions: list[tuple[int, str]] = []

        for pat in topic_intro_patterns:
            for match in re.finditer(pat, text, re.IGNORECASE):
                topic_str = self._clean_topic_phrase(match.group(1))
                if topic_str and len(topic_str) >= 3:
                    found_mentions.append((match.start(), topic_str))

        for pat in topic_transition_patterns:
            for match in re.finditer(pat, text, re.IGNORECASE):
                topic_str = self._clean_topic_phrase(match.group(1))
                if topic_str and len(topic_str) >= 3:
                    found_mentions.append((match.start(), topic_str))

        found_mentions.sort(key=lambda x: x[0])

        topic_sequence: list[str] = []
        for _, topic_name in found_mentions:
            if not topic_sequence or topic_sequence[-1].lower() != topic_name.lower():
                topic_sequence.append(topic_name)

        if not topic_sequence:
            for term in self.COMMON_TECHNICAL_KEYWORDS:
                if re.search(r"\b" + re.escape(term) + r"\b", text, re.IGNORECASE):
                    topic_sequence.append(" ".join(word.capitalize() for word in term.split()))
                    break

        if not topic_sequence:
            first_sentence = text.split(".")[0]
            if first_sentence:
                words = [w for w in first_sentence.split() if len(w) > 3][:4]
                if words:
                    topic_sequence.append(" ".join(w.capitalize() for w in words))

        if not topic_sequence:
            topic_sequence = ["Classroom Lecture"]

        current_topic = topic_sequence[-1]
        topic_history = [{"topic": t, "timestamp": None} for t in topic_sequence]

        return current_topic, topic_history

    def _infer_topic(self, text: str) -> str:
        current_topic, _ = self._infer_topic_and_history(text)
        return current_topic

    def _extract_key_points(self, text: str) -> list[str]:
        sentences = [s.strip() for s in text.split(".") if len(s.strip()) > 15]
        if not sentences:
            return ["Review the lecture transcript for details."]
        return sentences[:4]

    def _extract_concepts(self, text: str, topic: str) -> list[str]:
        concepts = set()
        if topic and topic.lower() != "classroom lecture":
            concepts.add(topic)

        high_level_terms = [
            "supervised learning", "unsupervised learning", "reinforcement learning",
            "machine learning", "deep learning", "neural network",
            "model evaluation", "area of a circle", "newton's second law",
            "newton's first law", "pythagorean theorem", "database normalization",
            "acid properties", "relational database", "model accuracy",
        ]
        text_lower = text.lower()
        for hlt in high_level_terms:
            if hlt in text_lower:
                concepts.add(" ".join(w.capitalize() for w in hlt.split()))

        concept_patterns = [
            r"(?:concept of|theory of|principle of|framework of)\s+([A-Za-z0-9\s\-]+?)(?=[.,;]| and | with |\bis\b)",
            r"([A-Za-z0-9\s\-]+?)\s+(?:theory|framework|architecture|paradigm)\b",
        ]
        for pat in concept_patterns:
            for match in re.finditer(pat, text, re.IGNORECASE):
                extracted = match.group(1).strip()
                if 3 < len(extracted) < 40 and not any(w in extracted.lower() for w in ["today", "this", "that", "what"]):
                    concepts.add(" ".join(w.capitalize() for w in extracted.split()))

        if not concepts:
            concepts.add(topic if topic else "General Concept")

        return sorted(list(concepts))[:6]

    def _extract_technical_terms(self, text: str) -> list[str]:
        found_terms = set()
        text_lower = text.lower()

        for term in self.COMMON_TECHNICAL_KEYWORDS:
            if re.search(r"\b" + re.escape(term) + r"\b", text_lower):
                found_terms.add(term)

        candidates = re.findall(r"\b[a-z]{4,}(?:tion|sion|ing|ment|gorithm|metrics)\b", text_lower)
        ignored = {"starting", "going", "learning", "something", "anything", "nothing", "everything", "having", "being"}
        for word in candidates:
            if word not in ignored:
                found_terms.add(word)

        return sorted(list(found_terms))[:10]

    def _extract_numbers(self, text: str) -> list[str]:
        found_numbers = set()

        for m in re.finditer(r"\b(\d+(?:\.\d+)?)\s*(?:%|percent)\b", text, re.IGNORECASE):
            found_numbers.add(f"{m.group(1)}%")

        unit_pattern = r"\b(\d+(?:\.\d+)?)\s*(kg|g|mg|m/s\u00b2|m/s\^2|m/s|km/h|mph|km|m|cm|mm|\u00b0c|celsius|k|bytes|kb|mb|gb|tb|seconds|sec|minutes|min|hours|students|samples|items|steps|epochs|watts|volts|ohms)\b"
        for m in re.finditer(unit_pattern, text, re.IGNORECASE):
            val = m.group(1)
            raw_unit = m.group(2).lower()
            if raw_unit in ("m/s^2", "m/s\u00b2"):
                unit = "m/s\u00b2"
            elif raw_unit in ("\u00b0c", "celsius"):
                found_numbers.add(f"{val}\u00b0C")
                continue
            else:
                unit = raw_unit
            found_numbers.add(f"{val} {unit}")

        for m in re.finditer(r"\b(3\.14159|3\.14|2\.718|9\.81)\b", text):
            found_numbers.add(m.group(1))

        for m in re.finditer(r"\b(19\d\d|20\d\d)\b", text):
            found_numbers.add(m.group(1))

        for m in re.finditer(r"\b(\d+:\d+)\b", text):
            found_numbers.add(m.group(1))

        return sorted(list(found_numbers))

    def _extract_formulas(self, text: str) -> list[str]:
        found_formulas = set()
        for pattern, formula in self.FORMULA_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                found_formulas.add(formula)

        explicit_equations = re.findall(
            r"\b([A-Za-z][A-Za-z0-9_\(\)]*\s*=\s*[^.,;]+(?=[.,;]|\s+and|\s+where|$))",
            text,
        )
        for eq in explicit_equations:
            eq_cleaned = eq.strip()
            if 3 <= len(eq_cleaned) <= 50 and any(op in eq_cleaned for op in ["+", "-", "*", "/", "^", "\u03c0", "\u00b2"]):
                found_formulas.add(eq_cleaned)

        return sorted(list(found_formulas))

    def _attribute_speakers(self, raw_text: str, clean_text: str) -> list[dict[str, Any]]:
        speaker_pattern = re.compile(
            r"^(Teacher|Student|Unknown)\s*:\s*(.+)$",
            re.IGNORECASE | re.MULTILINE,
        )
        matches = list(speaker_pattern.finditer(raw_text))

        if matches:
            segments = []
            for m in matches:
                raw_speaker = m.group(1).capitalize()
                speaker = raw_speaker if raw_speaker in ("Teacher", "Student", "Unknown") else "Unknown"
                content = m.group(2).strip()
                if content:
                    segments.append({
                        "speaker": speaker,
                        "text": content,
                        "timestamp": None,
                    })
            if segments:
                return segments

        if not clean_text:
            return []

        return [
            {
                "speaker": "Teacher",
                "text": clean_text,
                "timestamp": None,
            }
        ]

    def _extract_important_points(self, text: str) -> list[str]:
        emphasis_patterns = [
            r"\b(?:remember\s+that|remember)\b",
            r"\b(?:an\s+important\s+point\s+is|important\s+point(?::|\s+is))\b",
            r"\b(?:note\s+that|please\s+note\s+that|it\s+is\s+worth\s+noting\s+that)\b",
            r"\b(?:the\s+key\s+difference\s+is|key\s+difference(?::|\s+is))\b",
            r"\b(?:keep\s+in\s+mind(?:\s+that)?)\b",
            r"\b(?:this\s+is\s+important|it\s+is\s+important\s+(?:to\s+note\s+that|that)?)\b",
            r"\b(?:most\s+importantly|crucial\s+point\s+is|crucial\s+to\s+note)\b",
            r"\b(?:do\s+not\s+forget(?:\s+that)?|don't\s+forget(?:\s+that)?)\b",
            r"\b(?:pay\s+special\s+attention\s+to|pay\s+attention\s+to)\b",
        ]
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
        points: list[str] = []
        seen = set()

        for s in sentences:
            s_clean = re.sub(r"^(?:Teacher|Student|Unknown)\s*:\s*", "", s, flags=re.IGNORECASE).strip()
            if any(re.search(pat, s_clean, re.IGNORECASE) for pat in emphasis_patterns):
                cleaned_point = re.sub(
                    r"^(?:remember\s+that|remember\s*,?|an\s+important\s+point\s+is\s+that|an\s+important\s+point\s+is|important\s+point\s*:\s*|note\s+that|please\s+note\s+that|keep\s+in\s+mind\s+that|keep\s+in\s+mind\s*,?|most\s+importantly\s*,?|do\s+not\s+forget\s+that|do\s+not\s+forget\s*,?|don't\s+forget\s+that|don't\s+forget\s*,?)\s*",
                    "",
                    s_clean,
                    flags=re.IGNORECASE,
                ).strip()
                if cleaned_point and len(cleaned_point) >= 10:
                    cleaned_point = cleaned_point[0].upper() + cleaned_point[1:]
                    if not cleaned_point.endswith((".", "!", "?")):
                        cleaned_point += "."
                    if cleaned_point.lower() not in seen:
                        seen.add(cleaned_point.lower())
                        points.append(cleaned_point)

        return points[:6]

    def _extract_definitions(self, text: str) -> list[dict[str, str]]:
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
        definitions: list[dict[str, str]] = []
        seen_terms = set()
        excluded_terms = {
            "this", "that", "it", "there", "here", "what", "which", "who", "today",
            "today's lecture", "the goal", "the idea", "an example", "for example",
            "one example", "remember", "note", "next", "one thing", "another thing",
            "he", "she", "we", "they", "you",
        }

        for s in sentences:
            s_clean = re.sub(r"^(?:Teacher|Student|Unknown)\s*:\s*", "", s, flags=re.IGNORECASE).strip()
            # Pattern 1: <Term> is [defined as] a/an/the ...
            m1 = re.search(
                r"\b([A-Za-z][A-Za-z0-9\s\-]{1,30}?)\s+is\s+(?:defined\s+as\s+)?(a\s+[^.!?]+|an\s+[^.!?]+|the\s+[^.!?]+|defined\s+as\s+[^.!?]+)",
                s_clean,
                re.IGNORECASE,
            )
            if m1:
                raw_term = m1.group(1).strip()
                raw_def = m1.group(2).strip()
                term = re.sub(r"^(?:a|an|the)\s+", "", raw_term, flags=re.IGNORECASE).strip()
                if term.lower() not in excluded_terms and len(term) >= 3 and len(raw_def) >= 10:
                    term_cap = " ".join(w.capitalize() for w in term.split())
                    def_clean = re.sub(r"^defined\s+as\s+", "", raw_def, flags=re.IGNORECASE).strip()
                    def_clean = def_clean[0].upper() + def_clean[1:]
                    if not def_clean.endswith((".", "!", "?")):
                        def_clean += "."
                    if term_cap.lower() not in seen_terms:
                        seen_terms.add(term_cap.lower())
                        definitions.append({"term": term_cap, "definition": def_clean})
                    continue

            # Pattern 2: <Term> refers to / means ...
            m2 = re.search(
                r"\b([A-Za-z][A-Za-z0-9\s\-]{1,30}?)\s+(?:refers\s+to|means)\s+([^.!?]+)",
                s_clean,
                re.IGNORECASE,
            )
            if m2:
                raw_term = m2.group(1).strip()
                raw_def = m2.group(2).strip()
                term = re.sub(r"^(?:a|an|the)\s+", "", raw_term, flags=re.IGNORECASE).strip()
                if term.lower() not in excluded_terms and len(term) >= 3 and len(raw_def) >= 10:
                    term_cap = " ".join(w.capitalize() for w in term.split())
                    def_clean = raw_def[0].upper() + raw_def[1:]
                    if not def_clean.endswith((".", "!", "?")):
                        def_clean += "."
                    if term_cap.lower() not in seen_terms:
                        seen_terms.add(term_cap.lower())
                        definitions.append({"term": term_cap, "definition": def_clean})

        return definitions[:6]

    def _extract_examples(self, text: str, topic: str) -> list[dict[str, str]]:
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
        examples: list[dict[str, str]] = []
        seen = set()

        for s in sentences:
            s_clean = re.sub(r"^(?:Teacher|Student|Unknown)\s*:\s*", "", s, flags=re.IGNORECASE).strip()
            # Pattern A: For example / For instance, <example> is a <concept> problem/task/application
            mA = re.search(
                r"(?:for\s+example|for\s+instance)\s*,?\s*([^.!?]+?)\s+is\s+(?:an?\s+)?([A-Za-z0-9\s\-]+?)\s+(?:problem|task|application|example|method)\b",
                s_clean,
                re.IGNORECASE,
            )
            if mA:
                ex_text = mA.group(1).strip()
                concept_text = mA.group(2).strip()
                concept_cap = " ".join(w.capitalize() for w in concept_text.split())
                ex_cap = ex_text[0].upper() + ex_text[1:]
                key = (concept_cap.lower(), ex_cap.lower())
                if key not in seen and len(ex_cap) >= 3:
                    seen.add(key)
                    examples.append({"concept": concept_cap, "example": ex_cap})
                    continue

            # Pattern B: An example of <concept> is <example>
            mB = re.search(
                r"(?:an\s+example\s+of|an\s+instance\s+of)\s+([A-Za-z0-9\s\-]+?)\s+is\s+([^.!?]+)",
                s_clean,
                re.IGNORECASE,
            )
            if mB:
                concept_text = mB.group(1).strip()
                ex_text = mB.group(2).strip()
                concept_cap = " ".join(w.capitalize() for w in concept_text.split())
                ex_cap = ex_text[0].upper() + ex_text[1:]
                key = (concept_cap.lower(), ex_cap.lower())
                if key not in seen and len(ex_cap) >= 3:
                    seen.add(key)
                    examples.append({"concept": concept_cap, "example": ex_cap})
                    continue

            # Pattern C: Generic "For example, <ex>" or "such as <ex>"
            mC = re.search(
                r"(?:for\s+example|for\s+instance|such\s+as)\s*,?\s*([^.!?]+)",
                s_clean,
                re.IGNORECASE,
            )
            if mC:
                raw_ex = mC.group(1).strip()
                concept_name = topic if topic and topic.lower() != "classroom lecture" else "General"
                for kw in self.COMMON_TECHNICAL_KEYWORDS:
                    if re.search(r"\b" + re.escape(kw) + r"\b", s_clean, re.IGNORECASE):
                        concept_name = " ".join(w.capitalize() for w in kw.split())
                        break
                ex_cap = raw_ex[0].upper() + raw_ex[1:]
                key = (concept_name.lower(), ex_cap.lower())
                if key not in seen and len(ex_cap) >= 3:
                    seen.add(key)
                    examples.append({"concept": concept_name, "example": ex_cap})

        return examples[:6]

    def _extract_important_moments(
        self,
        definitions: list[dict[str, str]],
        formulas: list[str],
        important_points: list[str],
        examples: list[dict[str, str]],
        text: str,
    ) -> list[dict[str, Any]]:
        moments: list[dict[str, Any]] = []
        seen = set()

        # Definitions
        for d in definitions:
            content = f"{d['term']}: {d['definition']}"
            if content.lower() not in seen:
                seen.add(content.lower())
                moments.append({
                    "type": "definition",
                    "content": content,
                    "timestamp": None,
                })

        # Formulas
        for f in formulas:
            if f.lower() not in seen:
                seen.add(f.lower())
                moments.append({
                    "type": "formula",
                    "content": f,
                    "timestamp": None,
                })

        # Important Points
        for p in important_points:
            if p.lower() not in seen:
                seen.add(p.lower())
                moments.append({
                    "type": "important_point",
                    "content": p,
                    "timestamp": None,
                })

        # Examples
        for ex in examples:
            content = f"{ex['concept']} example: {ex['example']}"
            if content.lower() not in seen:
                seen.add(content.lower())
                moments.append({
                    "type": "example",
                    "content": content,
                    "timestamp": None,
                })

        # Warnings / Pitfalls
        warning_pattern = r"\b(?:be\s+careful\s+not\s+to|be\s+careful\s+when|watch\s+out\s+for|a\s+common\s+mistake\s+is|common\s+pitfall|do\s+not\s+confuse|don't\s+confuse|warning\s*:|caution\s*:)\b"
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
        for s in sentences:
            s_clean = re.sub(r"^(?:Teacher|Student|Unknown)\s*:\s*", "", s, flags=re.IGNORECASE).strip()
            if re.search(warning_pattern, s_clean, re.IGNORECASE):
                if s_clean.lower() not in seen:
                    seen.add(s_clean.lower())
                    moments.append({
                        "type": "warning",
                        "content": s_clean,
                        "timestamp": None,
                    })

        return moments[:10]


def _parse_structured_json(parsed: dict[str, Any], fallback_text: str) -> dict[str, Any]:
    segments = []
    for seg in parsed.get("speaker_segments", []):
        if isinstance(seg, dict):
            speaker = seg.get("speaker")
            if speaker not in ("Teacher", "Student", "Unknown"):
                speaker = "Unknown"
            segments.append({
                "speaker": speaker,
                "text": str(seg.get("text", "")).strip(),
                "timestamp": seg.get("timestamp"),
            })
    if not segments and fallback_text.strip():
        segments = [{"speaker": "Teacher", "text": fallback_text.strip(), "timestamp": None}]

    topic_str = str(parsed.get("topic", "Lecture Notes")).strip()

    topic_history_raw = parsed.get("topic_history", [])
    topic_history = []
    if isinstance(topic_history_raw, list):
        for th in topic_history_raw:
            if isinstance(th, dict) and th.get("topic"):
                topic_history.append({
                    "topic": str(th["topic"]).strip(),
                    "timestamp": th.get("timestamp"),
                })
    if not topic_history and topic_str:
        topic_history = [{"topic": topic_str, "timestamp": None}]

    important_points = [
        str(ip).strip()
        for ip in parsed.get("important_points", [])
        if str(ip).strip()
    ]

    definitions_raw = parsed.get("definitions", [])
    definitions = []
    if isinstance(definitions_raw, list):
        for d in definitions_raw:
            if isinstance(d, dict) and d.get("term") and d.get("definition"):
                definitions.append({
                    "term": str(d["term"]).strip(),
                    "definition": str(d["definition"]).strip(),
                })

    examples_raw = parsed.get("examples", [])
    examples = []
    if isinstance(examples_raw, list):
        for ex in examples_raw:
            if isinstance(ex, dict) and ex.get("concept") and ex.get("example"):
                examples.append({
                    "concept": str(ex["concept"]).strip(),
                    "example": str(ex["example"]).strip(),
                })

    important_moments_raw = parsed.get("important_moments", [])
    important_moments = []
    if isinstance(important_moments_raw, list):
        for im in important_moments_raw:
            if isinstance(im, dict) and im.get("type") and im.get("content"):
                important_moments.append({
                    "type": str(im["type"]).strip(),
                    "content": str(im["content"]).strip(),
                    "timestamp": im.get("timestamp"),
                })

    return {
        "clean_text": str(parsed.get("clean_text", "")).strip(),
        "topic": topic_str,
        "key_points": [str(kp).strip() for kp in parsed.get("key_points", []) if str(kp).strip()],
        "concepts": [str(c).strip() for c in parsed.get("concepts", []) if str(c).strip()],
        "technical_terms": [str(t).strip() for t in parsed.get("technical_terms", []) if str(t).strip()],
        "numbers": [str(n).strip() for n in parsed.get("numbers", []) if str(n).strip()],
        "formulas": [str(f).strip() for f in parsed.get("formulas", []) if str(f).strip()],
        "speaker_segments": segments,
        "topic_history": topic_history,
        "important_points": important_points,
        "definitions": definitions,
        "examples": examples,
        "important_moments": important_moments,
    }


class GeminiAIProvider(AIProvider):
    """Google Gemini AI provider using generateContent REST API."""

    def __init__(self, api_key: str | None = None, model: str = "gemini-1.5-flash"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.model = model
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"

    async def structure_transcript(self, text: str) -> dict[str, Any]:
        if not self.api_key:
            raise AIStructuringError("GEMINI_API_KEY is not configured.")

        url = f"{self.base_url}/{self.model}:generateContent?key={self.api_key}"
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": f"{SYSTEM_PROMPT}\n\nTRANSCRIPT TO STRUCTURE:\n{text}"}
                    ],
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.2,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.post(url, json=payload)
                if res.status_code != 200:
                    raise AIStructuringError(f"Gemini API returned {res.status_code}: {res.text}")
                data = res.json()
        except httpx.RequestError as exc:
            raise AIStructuringError(f"Network error communicating with Gemini API: {exc}") from exc

        return self._parse_json_result(data, text)

    async def answer_question(
        self,
        question: str,
        lecture_text: str,
        conversation_history: list[dict[str, Any]] | None = None,
        lecture_structured_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not self.api_key:
            raise AIStructuringError("GEMINI_API_KEY is not configured.")

        url = f"{self.base_url}/{self.model}:generateContent?key={self.api_key}"
        history_text = ""
        if conversation_history:
            history_lines = []
            for msg in conversation_history[-10:]:
                role = "Student" if msg.get("role") == "user" else "Assistant"
                content = msg.get("content", "")
                history_lines.append(f"{role}: {content}")
            if history_lines:
                history_text = "\nRECENT CONVERSATION HISTORY:\n" + "\n".join(history_lines) + "\n"

        prompt = (
            f"{QA_SYSTEM_PROMPT}\n\n"
            f"LECTURE CONTENT:\n{lecture_text}\n"
            f"{history_text}\n"
            f"CURRENT STUDENT QUESTION:\n{question}"
        )
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.1,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.post(url, json=payload)
                if res.status_code != 200:
                    raise AIStructuringError(f"Gemini API returned {res.status_code}: {res.text}")
                data = res.json()
        except httpx.RequestError as exc:
            raise AIStructuringError(f"Network error communicating with Gemini API: {exc}") from exc

        return self._parse_qa_result(data, question)

    def _parse_json_result(self, response_data: dict, fallback_text: str) -> dict[str, Any]:
        try:
            candidates = response_data.get("candidates", [])
            if not candidates:
                raise ValueError("No candidates returned from Gemini.")
            raw_json_str = candidates[0]["content"]["parts"][0]["text"]
            parsed = json.loads(raw_json_str)
            return _parse_structured_json(parsed, fallback_text)
        except (KeyError, json.JSONDecodeError, ValueError) as exc:
            raise AIStructuringError(f"Failed to parse Gemini structuring response: {exc}") from exc

    def _parse_qa_result(self, response_data: dict, question: str) -> dict[str, Any]:
        try:
            candidates = response_data.get("candidates", [])
            if not candidates:
                raise ValueError("No candidates returned from Gemini.")
            raw_json_str = candidates[0]["content"]["parts"][0]["text"]
            parsed = json.loads(raw_json_str)
            return {
                "question": question,
                "answer": str(parsed.get("answer", "This was not covered in the current lecture.")).strip(),
                "sources": [str(s).strip() for s in parsed.get("sources", []) if str(s).strip()],
                "lecture_grounded": bool(parsed.get("lecture_grounded", False)),
            }
        except (KeyError, json.JSONDecodeError, ValueError) as exc:
            raise AIStructuringError(f"Failed to parse Gemini Q&A response: {exc}") from exc


class OpenAIAIProvider(AIProvider):
    """OpenAI API provider."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.url = "https://api.openai.com/v1/chat/completions"

    def _missing_key_error(self) -> AIStructuringError:
        return AIStructuringError("OPENAI_API_KEY is not configured.")

    def _request_error(self, response: httpx.Response) -> AIStructuringError:
        return AIStructuringError(f"OpenAI API returned {response.status_code}: {response.text}")

    def _network_error(self, error: Exception) -> AIStructuringError:
        return AIStructuringError(f"Network error communicating with OpenAI API: {error}")

    def _structure_parse_error(self, error: Exception) -> AIStructuringError:
        return AIStructuringError(f"Failed to parse OpenAI structuring response: {error}")

    def _qa_parse_error(self, error: Exception) -> AIStructuringError:
        return AIStructuringError(f"Failed to parse OpenAI Q&A response: {error}")

    async def structure_transcript(self, text: str) -> dict[str, Any]:
        if not self.api_key:
            raise self._missing_key_error()

        payload = {
            "model": self.model,
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"TRANSCRIPT TO STRUCTURE:\n{text}"},
            ],
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.post(self.url, json=payload, headers=headers)
                if res.status_code != 200:
                    raise self._request_error(res)
                data = res.json()
        except httpx.RequestError as exc:
            raise self._network_error(exc) from exc

        return self._parse_json_result(data, text)

    async def answer_question(
        self,
        question: str,
        lecture_text: str,
        conversation_history: list[dict[str, Any]] | None = None,
        lecture_structured_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not self.api_key:
            raise self._missing_key_error()

        messages = [
            {"role": "system", "content": QA_SYSTEM_PROMPT},
            {"role": "user", "content": f"LECTURE CONTENT:\n{lecture_text}"},
        ]
        if conversation_history:
            for msg in conversation_history[-10:]:
                role = "user" if msg.get("role") == "user" else "assistant"
                messages.append({"role": role, "content": msg.get("content", "")})
        messages.append({"role": "user", "content": question})

        payload = {
            "model": self.model,
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
            "messages": messages,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.post(self.url, json=payload, headers=headers)
                if res.status_code != 200:
                    raise self._request_error(res)
                data = res.json()
        except httpx.RequestError as exc:
            raise self._network_error(exc) from exc

        return self._parse_qa_result(data, question)

    def _parse_json_result(self, response_data: dict, fallback_text: str) -> dict[str, Any]:
        try:
            raw_json_str = response_data["choices"][0]["message"]["content"]
            parsed = json.loads(raw_json_str)
            return _parse_structured_json(parsed, fallback_text)
        except (KeyError, json.JSONDecodeError, ValueError) as exc:
            raise self._structure_parse_error(exc) from exc

    def _parse_qa_result(self, response_data: dict, question: str) -> dict[str, Any]:
        try:
            raw_json_str = response_data["choices"][0]["message"]["content"]
            parsed = json.loads(raw_json_str)
            return {
                "question": question,
                "answer": str(parsed.get("answer", "This was not covered in the current lecture.")).strip(),
                "sources": [str(s).strip() for s in parsed.get("sources", []) if str(s).strip()],
                "lecture_grounded": bool(parsed.get("lecture_grounded", False)),
            }
        except (KeyError, json.JSONDecodeError, ValueError) as exc:
            raise self._qa_parse_error(exc) from exc


class GroqAIProvider(OpenAIAIProvider):
    """Groq's OpenAI-compatible chat-completions provider."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY", "")
        self.model = model or os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
        base_url = os.getenv(
            "GROQ_BASE_URL",
            "https://api.groq.com/openai/v1",
        ).rstrip("/")
        self.url = f"{base_url}/chat/completions"

    def _missing_key_error(self) -> AIStructuringError:
        return AIStructuringError("GROQ_API_KEY is not configured.")

    def _request_error(self, response: httpx.Response) -> AIStructuringError:
        return AIStructuringError(f"Groq API returned {response.status_code}: {response.text}")

    def _network_error(self, error: Exception) -> AIStructuringError:
        return AIStructuringError(f"Network error communicating with Groq API: {error}")

    def _structure_parse_error(self, error: Exception) -> AIStructuringError:
        return AIStructuringError(f"Failed to parse Groq structuring response: {error}")

    def _qa_parse_error(self, error: Exception) -> AIStructuringError:
        return AIStructuringError(f"Failed to parse Groq Q&A response: {error}")


class AIStructuringService:
    """Singleton service manager for lecture structuring and Q&A."""

    def __init__(self):
        selected_provider = os.getenv("AI_PROVIDER", "auto").strip().lower()

        if selected_provider in {"heuristic", "local", "none"}:
            self._provider: AIProvider = HeuristicAIProvider()
        elif selected_provider == "groq":
            self._provider = GroqAIProvider() if os.getenv("GROQ_API_KEY", "").strip() else HeuristicAIProvider()
        elif selected_provider == "openai":
            self._provider = OpenAIAIProvider() if os.getenv("OPENAI_API_KEY", "").strip() else HeuristicAIProvider()
        elif selected_provider == "gemini":
            self._provider = GeminiAIProvider() if os.getenv("GEMINI_API_KEY", "").strip() else HeuristicAIProvider()
        elif selected_provider in {"", "auto"}:
            if os.getenv("GEMINI_API_KEY", "").strip():
                self._provider = GeminiAIProvider()
            elif os.getenv("GROQ_API_KEY", "").strip():
                self._provider = GroqAIProvider()
            elif os.getenv("OPENAI_API_KEY", "").strip():
                self._provider = OpenAIAIProvider()
            else:
                self._provider = HeuristicAIProvider()
        else:
            raise ValueError(
                f"Unsupported AI_PROVIDER '{selected_provider}'. Use groq, openai, gemini, heuristic, or auto."
            )

    def set_provider(self, provider: AIProvider) -> None:
        """Swap provider dynamically (used for testing or runtime reconfiguration)."""
        self._provider = provider

    async def structure_transcript(self, text: str) -> dict[str, Any]:
        cleaned = text.strip()
        if not cleaned:
            raise ValueError("Transcript text cannot be empty.")
        return await self._provider.structure_transcript(cleaned)

    async def answer_question(
        self,
        question: str,
        lecture_text: str,
        conversation_history: list[dict[str, Any]] | None = None,
        lecture_structured_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        q_cleaned = question.strip()
        if not q_cleaned:
            raise ValueError("Question cannot be empty.")
        try:
            return await self._provider.answer_question(
                q_cleaned,
                lecture_text,
                conversation_history=conversation_history,
                lecture_structured_data=lecture_structured_data,
            )
        except TypeError as err:
            if "unexpected keyword argument" in str(err):
                return await self._provider.answer_question(q_cleaned, lecture_text)
            raise


ai_structuring_service = AIStructuringService()
