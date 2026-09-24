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

You must respond with ONLY a valid JSON object matching this schema:
{
  "clean_text": "Cleaned, structured lecture text with fillers removed and clear formatting",
  "topic": "Concise subject or topic title",
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
  ]
}
"""

QA_SYSTEM_PROMPT = """You are an educational assistant answering student questions about a specific lecture.

CRITICAL RULES:
1. Use ONLY the supplied lecture content as the source of truth.
2. Do NOT use outside knowledge or introduce external facts.
3. If the answer cannot be found or reasonably derived from the lecture content, you must explicitly state: "This was not covered in the current lecture."
4. Do NOT invent or hallucinate facts, definitions, formulas, examples, numbers, or concepts not supported by the lecture.
5. Provide a concise, student-friendly answer directly addressing the question.
6. If the student asks to explain something simply, simplify the concept using ONLY the facts provided in the lecture.
7. Include the exact relevant sentence or snippet from the lecture in the "sources" list.
8. If the question was not covered, return "lecture_grounded": false and "sources": []. If answered from the lecture, return "lecture_grounded": true.

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
    async def answer_question(self, question: str, lecture_text: str) -> dict[str, Any]:
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
        topic = self._infer_topic(cleaned)
        key_points = self._extract_key_points(cleaned)
        concepts = self._extract_concepts(cleaned, topic)
        technical_terms = self._extract_technical_terms(cleaned)
        numbers = self._extract_numbers(cleaned)
        formulas = self._extract_formulas(text + " " + cleaned)
        speaker_segments = self._attribute_speakers(text, cleaned)

        return {
            "clean_text": cleaned,
            "topic": topic,
            "key_points": key_points,
            "concepts": concepts,
            "technical_terms": technical_terms,
            "numbers": numbers,
            "formulas": formulas,
            "speaker_segments": speaker_segments,
        }

    async def answer_question(self, question: str, lecture_text: str) -> dict[str, Any]:
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

        # Split lecture into sentences
        sentences = [
            s.strip()
            for s in re.split(r"(?<=[.!?])\s+|\n+", lec_clean)
            if s.strip()
        ]

        # 1. Formula questions
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

        # 2. Number / measurement questions
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

        # 3. Topic, Concept, or General Content questions
        stop_words = {
            "what", "is", "are", "the", "a", "an", "and", "or", "in", "on", "at", "to", "for", "of",
            "with", "did", "does", "do", "how", "why", "can", "you", "tell", "me", "about", "explain",
            "simply", "simple", "teacher", "mention", "lecture", "taught", "today", "study", "class",
            "use", "uses", "used", "using", "which", "who", "whom", "where", "when", "there", "their",
            "have", "has", "had", "having", "give", "gives", "given", "giving",
        }
        words = re.findall(r"[a-z0-9\u00b0\u00b2\u03c0]+", q_lower)
        keywords = [w for w in words if w not in stop_words and len(w) > 1]

        best_sentence = None
        best_score = 0

        for s in sentences:
            s_lower = s.lower()
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
                if any(p in clean_s_lower for p in [" is ", " are ", " refers to ", " means ", " predict"]):
                    score += 1

            if len(keywords) >= 2 and kws_matched < 2 and score < 6:
                continue

            if score > best_score and kws_matched >= 1:
                best_score = score
                best_sentence = clean_s

        if best_sentence and best_score >= 2:
            answer_text = best_sentence
            if "simply" in q_lower or "simple" in q_lower:
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

    def _infer_topic(self, text: str) -> str:
        patterns = [
            r"today we are (?:going to )?(?:study|discuss|learn|focus on) (?:the )?(?:concept of )?([^.,!?;]+)",
            r"today's lecture is about ([^.,!?;]+)",
            r"we are covering ([^.,!?;]+)",
            r"let us discuss ([^.,!?;]+)",
            r"introduction to ([^.,!?;]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                raw_topic = match.group(1).strip()
                words = [w.capitalize() for w in raw_topic.split() if w.lower() not in {"a", "an", "the", "in", "of", "and"}]
                if words:
                    return " ".join(words)

        for term in self.COMMON_TECHNICAL_KEYWORDS:
            if re.search(r"\b" + re.escape(term) + r"\b", text, re.IGNORECASE):
                return " ".join(word.capitalize() for word in term.split())

        first_sentence = text.split(".")[0]
        if first_sentence:
            words = [w for w in first_sentence.split() if len(w) > 3][:4]
            if words:
                return " ".join(w.capitalize() for w in words)

        return "Classroom Lecture"

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

    async def answer_question(self, question: str, lecture_text: str) -> dict[str, Any]:
        if not self.api_key:
            raise AIStructuringError("GEMINI_API_KEY is not configured.")

        url = f"{self.base_url}/{self.model}:generateContent?key={self.api_key}"
        prompt = (
            f"{QA_SYSTEM_PROMPT}\n\n"
            f"LECTURE CONTENT:\n{lecture_text}\n\n"
            f"STUDENT QUESTION:\n{question}"
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

            segments = []
            for seg in parsed.get("speaker_segments", []):
                speaker = seg.get("speaker")
                if speaker not in ("Teacher", "Student", "Unknown"):
                    speaker = "Unknown"
                segments.append({
                    "speaker": speaker,
                    "text": seg.get("text", "").strip(),
                    "timestamp": seg.get("timestamp"),
                })
            if not segments and fallback_text.strip():
                segments = [{"speaker": "Teacher", "text": fallback_text.strip(), "timestamp": None}]

            return {
                "clean_text": str(parsed.get("clean_text", "")).strip(),
                "topic": str(parsed.get("topic", "Lecture Notes")).strip(),
                "key_points": [str(kp).strip() for kp in parsed.get("key_points", []) if str(kp).strip()],
                "concepts": [str(c).strip() for c in parsed.get("concepts", []) if str(c).strip()],
                "technical_terms": [str(t).strip() for t in parsed.get("technical_terms", []) if str(t).strip()],
                "numbers": [str(n).strip() for n in parsed.get("numbers", []) if str(n).strip()],
                "formulas": [str(f).strip() for f in parsed.get("formulas", []) if str(f).strip()],
                "speaker_segments": segments,
            }
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

    def __init__(self, api_key: str | None = None, model: str = "gpt-4o-mini"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.model = model
        self.url = "https://api.openai.com/v1/chat/completions"

    async def structure_transcript(self, text: str) -> dict[str, Any]:
        if not self.api_key:
            raise AIStructuringError("OPENAI_API_KEY is not configured.")

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
                    raise AIStructuringError(f"OpenAI API returned {res.status_code}: {res.text}")
                data = res.json()
        except httpx.RequestError as exc:
            raise AIStructuringError(f"Network error communicating with OpenAI API: {exc}") from exc

        return self._parse_json_result(data, text)

    async def answer_question(self, question: str, lecture_text: str) -> dict[str, Any]:
        if not self.api_key:
            raise AIStructuringError("OPENAI_API_KEY is not configured.")

        payload = {
            "model": self.model,
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
            "messages": [
                {"role": "system", "content": QA_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"LECTURE CONTENT:\n{lecture_text}\n\nSTUDENT QUESTION:\n{question}",
                },
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
                    raise AIStructuringError(f"OpenAI API returned {res.status_code}: {res.text}")
                data = res.json()
        except httpx.RequestError as exc:
            raise AIStructuringError(f"Network error communicating with OpenAI API: {exc}") from exc

        return self._parse_qa_result(data, question)

    def _parse_json_result(self, response_data: dict, fallback_text: str) -> dict[str, Any]:
        try:
            raw_json_str = response_data["choices"][0]["message"]["content"]
            parsed = json.loads(raw_json_str)

            segments = []
            for seg in parsed.get("speaker_segments", []):
                speaker = seg.get("speaker")
                if speaker not in ("Teacher", "Student", "Unknown"):
                    speaker = "Unknown"
                segments.append({
                    "speaker": speaker,
                    "text": seg.get("text", "").strip(),
                    "timestamp": seg.get("timestamp"),
                })
            if not segments and fallback_text.strip():
                segments = [{"speaker": "Teacher", "text": fallback_text.strip(), "timestamp": None}]

            return {
                "clean_text": str(parsed.get("clean_text", "")).strip(),
                "topic": str(parsed.get("topic", "Lecture Notes")).strip(),
                "key_points": [str(kp).strip() for kp in parsed.get("key_points", []) if str(kp).strip()],
                "concepts": [str(c).strip() for c in parsed.get("concepts", []) if str(c).strip()],
                "technical_terms": [str(t).strip() for t in parsed.get("technical_terms", []) if str(t).strip()],
                "numbers": [str(n).strip() for n in parsed.get("numbers", []) if str(n).strip()],
                "formulas": [str(f).strip() for f in parsed.get("formulas", []) if str(f).strip()],
                "speaker_segments": segments,
            }
        except (KeyError, json.JSONDecodeError, ValueError) as exc:
            raise AIStructuringError(f"Failed to parse OpenAI structuring response: {exc}") from exc

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
            raise AIStructuringError(f"Failed to parse OpenAI Q&A response: {exc}") from exc


class AIStructuringService:
    """Singleton service manager for lecture structuring and Q&A."""

    def __init__(self):
        if os.getenv("GEMINI_API_KEY"):
            self._provider: AIProvider = GeminiAIProvider()
        elif os.getenv("OPENAI_API_KEY"):
            self._provider = OpenAIAIProvider()
        else:
            self._provider = HeuristicAIProvider()

    def set_provider(self, provider: AIProvider) -> None:
        """Swap provider dynamically (used for testing or runtime reconfiguration)."""
        self._provider = provider

    async def structure_transcript(self, text: str) -> dict[str, Any]:
        cleaned = text.strip()
        if not cleaned:
            raise ValueError("Transcript text cannot be empty.")
        return await self._provider.structure_transcript(cleaned)

    async def answer_question(self, question: str, lecture_text: str) -> dict[str, Any]:
        q_cleaned = question.strip()
        if not q_cleaned:
            raise ValueError("Question cannot be empty.")
        return await self._provider.answer_question(q_cleaned, lecture_text)


ai_structuring_service = AIStructuringService()
