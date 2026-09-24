"""Tests for AI transcript structuring, speaker attribution, numbers, formulas,
concepts, terms, and lecture-grounded Q&A.
"""

import asyncio
import pytest
from pydantic import ValidationError

from app.models import LectureQARequest, SpeakerSegment
from app.services.ai_structuring import (
    AIProvider,
    AIStructuringError,
    HeuristicAIProvider,
    ai_structuring_service,
)


class MockFailingProvider(AIProvider):
    """Provider that simulates an LLM API outage or rate limit error."""

    async def structure_transcript(self, text: str):
        raise AIStructuringError("Upstream model service timeout.")

    async def answer_question(self, question: str, lecture_text: str, *args, **kwargs):
        raise AIStructuringError("Upstream Q&A model service timeout.")


class MockSuccessProvider(AIProvider):
    """Provider returning predictable structured output and Q&A for testing."""

    async def structure_transcript(self, text: str):
        return {
            "clean_text": "The model achieved 95% accuracy with 10 kg payload. F = ma.",
            "topic": "Physics and Machine Learning",
            "key_points": [
                "The model achieved 95% accuracy",
                "Force equals mass times acceleration",
            ],
            "concepts": [
                "Model Accuracy",
                "Newton's Second Law",
            ],
            "technical_terms": [
                "accuracy",
                "acceleration",
            ],
            "numbers": [
                "95%",
                "10 kg",
            ],
            "formulas": [
                "F = ma",
            ],
            "speaker_segments": [
                {
                    "speaker": "Teacher",
                    "text": "The model achieved 95% accuracy with 10 kg payload. F = ma.",
                    "timestamp": None,
                }
            ],
            "topic_history": [
                {"topic": "Physics and Machine Learning", "timestamp": None}
            ],
            "important_points": [
                "Force equals mass times acceleration."
            ],
            "definitions": [
                {"term": "Force", "definition": "Mass times acceleration."}
            ],
            "examples": [
                {"concept": "Newton's Second Law", "example": "10 kg payload accelerating"}
            ],
            "important_moments": [
                {"type": "formula", "content": "F = ma", "timestamp": None}
            ],
        }

    async def answer_question(self, question: str, lecture_text: str, *args, **kwargs):
        if "france" in question.lower():
            return {
                "question": question,
                "answer": "This was not covered in the current lecture.",
                "sources": [],
                "lecture_grounded": False,
            }
        return {
            "question": question,
            "answer": "Supervised learning uses labelled training data.",
            "sources": ["Supervised learning uses labelled training data."],
            "lecture_grounded": True,
        }


@pytest.fixture(autouse=True)
def reset_provider():
    """Ensure the global service provider is restored after each test."""
    original = ai_structuring_service._provider
    yield
    ai_structuring_service.set_provider(original)


# 1. Successful lecture-grounded Q&A
def test_successful_lecture_grounded_qa(client):
    session = client.post("/api/sessions").json()
    session_id = session["session_id"]

    client.post(
        f"/api/sessions/{session_id}/transcript",
        json={"text": "Supervised learning uses labelled training data. Classification predicts discrete categories."},
    )

    response = client.post(
        f"/api/sessions/{session_id}/qa",
        json={"question": "What is supervised learning?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["question"] == "What is supervised learning?"
    assert "labelled training data" in data["answer"].lower()
    assert data["lecture_grounded"] is True
    assert len(data["sources"]) >= 1
    assert any("labelled training data" in s.lower() for s in data["sources"])


# 2. Question validation
def test_question_validation(client):
    session = client.post("/api/sessions").json()
    session_id = session["session_id"]

    res_missing = client.post(f"/api/sessions/{session_id}/qa", json={})
    assert res_missing.status_code == 422

    res_type = client.post(f"/api/sessions/{session_id}/qa", json={"question": 12345})
    assert res_type.status_code == 422


# 3. Empty question
def test_empty_question(client):
    session = client.post("/api/sessions").json()
    session_id = session["session_id"]

    client.post(
        f"/api/sessions/{session_id}/transcript",
        json={"text": "Supervised learning uses labelled training data."},
    )

    res_empty = client.post(
        f"/api/sessions/{session_id}/qa",
        json={"question": "   "},
    )
    assert res_empty.status_code == 400
    assert "empty" in res_empty.json()["detail"].lower()


# 4. Invalid session
def test_invalid_session_qa(client):
    res = client.post(
        "/api/sessions/NONEXISTENT99/qa",
        json={"question": "What is machine learning?"},
    )
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


# 5. Empty lecture
def test_empty_lecture_qa(client):
    session = client.post("/api/sessions").json()
    session_id = session["session_id"]

    res = client.post(
        f"/api/sessions/{session_id}/qa",
        json={"question": "What is machine learning?"},
    )
    assert res.status_code == 400
    assert "not contain enough content" in res.json()["detail"]


# 6. Question answered directly from lecture content
def test_question_answered_from_lecture_content():
    provider = HeuristicAIProvider()
    lecture = "Supervised learning uses labelled training data. It trains models to map inputs to outputs."
    question = "What does supervised learning use?"

    result = asyncio.run(provider.answer_question(question, lecture))
    assert result["lecture_grounded"] is True
    assert "labelled training data" in result["answer"].lower()
    assert len(result["sources"]) == 1


# 7. Question not covered by lecture
def test_question_not_covered_by_lecture(client):
    session = client.post("/api/sessions").json()
    session_id = session["session_id"]

    client.post(
        f"/api/sessions/{session_id}/transcript",
        json={"text": "Today we covered photosynthesis and plant biology in the laboratory."},
    )

    response = client.post(
        f"/api/sessions/{session_id}/qa",
        json={"question": "What is the capital of France?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["lecture_grounded"] is False
    assert "not covered" in data["answer"].lower()
    assert data["sources"] == []


# 8. Formula question
def test_formula_question_qa(client):
    session = client.post("/api/sessions").json()
    session_id = session["session_id"]

    client.post(
        f"/api/sessions/{session_id}/transcript",
        json={"text": "In physics, force equals mass times acceleration. F = ma."},
    )

    response = client.post(
        f"/api/sessions/{session_id}/qa",
        json={"question": "What formula did the teacher mention?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["lecture_grounded"] is True
    assert "F = ma" in data["answer"]
    assert len(data["sources"]) >= 1


# 9. Concept question
def test_concept_question_qa(client):
    session = client.post("/api/sessions").json()
    session_id = session["session_id"]

    client.post(
        f"/api/sessions/{session_id}/transcript",
        json={"text": "Today we are learning about Supervised Learning in Machine Learning."},
    )

    response = client.post(
        f"/api/sessions/{session_id}/qa",
        json={"question": "Explain supervised learning simply."},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["lecture_grounded"] is True
    assert "supervised learning" in data["answer"].lower()


# 10. Technical-term question
def test_technical_term_question_qa(client):
    session = client.post("/api/sessions").json()
    session_id = session["session_id"]

    client.post(
        f"/api/sessions/{session_id}/transcript",
        json={"text": "Classification predicts discrete labels while regression predicts continuous numbers."},
    )

    response = client.post(
        f"/api/sessions/{session_id}/qa",
        json={"question": "What is classification?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["lecture_grounded"] is True
    assert "discrete labels" in data["answer"].lower() or "predict" in data["answer"].lower()
    assert len(data["sources"]) >= 1


# 11. Source snippets returned
def test_source_snippets_returned(client):
    session = client.post("/api/sessions").json()
    session_id = session["session_id"]

    sentence = "Supervised learning uses labelled training data."
    client.post(
        f"/api/sessions/{session_id}/transcript",
        json={"text": f"{sentence} Another unrelated sentence is here."},
    )

    response = client.post(
        f"/api/sessions/{session_id}/qa",
        json={"question": "What is supervised learning?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["sources"], list)
    assert len(data["sources"]) >= 1
    assert all(isinstance(s, str) and len(s) > 0 for s in data["sources"])
    assert any(sentence.lower() in s.lower() for s in data["sources"])


# 12. AI provider failure returns 503
def test_ai_provider_failure_returns_503(client):
    ai_structuring_service.set_provider(MockFailingProvider())

    session = client.post("/api/sessions").json()
    session_id = session["session_id"]

    client.post(
        f"/api/sessions/{session_id}/transcript",
        json={"text": "Today we study Supervised Learning."},
    )

    res_structure = client.post(f"/api/sessions/{session_id}/structure")
    assert res_structure.status_code == 503
    assert "unavailable" in res_structure.json()["detail"].lower()

    res_qa = client.post(
        f"/api/sessions/{session_id}/qa",
        json={"question": "What is supervised learning?"},
    )
    assert res_qa.status_code == 503
    assert "unavailable" in res_qa.json()["detail"].lower()


# 13. Heuristic fallback
def test_heuristic_fallback_without_api_key(client):
    ai_structuring_service.set_provider(HeuristicAIProvider())

    session = client.post("/api/sessions").json()
    session_id = session["session_id"]

    client.post(
        f"/api/sessions/{session_id}/transcript",
        json={"text": "Voltage equals current times resistance. V = IR."},
    )

    res_qa = client.post(
        f"/api/sessions/{session_id}/qa",
        json={"question": "What is the formula for voltage?"},
    )
    assert res_qa.status_code == 200
    data = res_qa.json()
    assert data["lecture_grounded"] is True
    assert "V = IR" in data["answer"]


# 14. Session isolation (Session A vs Session B)
def test_session_isolation_qa(client):
    # Session A: Machine Learning lecture
    session_a = client.post("/api/sessions").json()["session_id"]
    client.post(
        f"/api/sessions/{session_a}/transcript",
        json={"text": "Supervised learning uses labelled training data for classification."},
    )

    # Session B: Relational Database lecture
    session_b = client.post("/api/sessions").json()["session_id"]
    client.post(
        f"/api/sessions/{session_b}/transcript",
        json={"text": "Relational databases use SQL and primary keys for indexing."},
    )

    # Asking about databases in Session A MUST NOT see Session B's content
    res_a = client.post(
        f"/api/sessions/{session_a}/qa",
        json={"question": "What do relational databases use?"},
    )
    assert res_a.status_code == 200
    data_a = res_a.json()
    assert data_a["lecture_grounded"] is False
    assert "not covered" in data_a["answer"].lower()

    # Asking about databases in Session B should be grounded and answered
    res_b = client.post(
        f"/api/sessions/{session_b}/qa",
        json={"question": "What do relational databases use?"},
    )
    assert res_b.status_code == 200
    data_b = res_b.json()
    assert data_b["lecture_grounded"] is True
    assert any(term in data_b["answer"].lower() for term in ["sql", "primary key", "relational"])


# 15. Existing structured response still works
def test_existing_structured_response_still_works(client):
    session = client.post("/api/sessions").json()
    session_id = session["session_id"]

    client.post(
        f"/api/sessions/{session_id}/transcript",
        json={"text": "Today we study Supervised Learning and Model Evaluation in AI."},
    )
    client.post(
        f"/api/sessions/{session_id}/transcript",
        json={"text": "The classification accuracy of the model is 95 percent. V equals I R for sensors."},
    )

    response = client.post(f"/api/sessions/{session_id}/structure")
    assert response.status_code == 200
    data = response.json()

    assert "clean_text" in data
    assert "topic" in data
    assert "key_points" in data
    assert "concepts" in data
    assert "technical_terms" in data
    assert "numbers" in data
    assert "formulas" in data
    assert "speaker_segments" in data

    assert isinstance(data["key_points"], list)
    assert isinstance(data["concepts"], list)
    assert isinstance(data["technical_terms"], list)
    assert isinstance(data["numbers"], list)
    assert isinstance(data["formulas"], list)
    assert isinstance(data["speaker_segments"], list)


# 16. Existing speaker attribution still works
def test_existing_speaker_attribution_still_works():
    provider = HeuristicAIProvider()
    raw = (
        "Teacher: Today we study algorithms.\n"
        "Student: What is an algorithm?\n"
        "Teacher: An algorithm is a sequence of steps."
    )
    result = asyncio.run(provider.structure_transcript(raw))
    segments = result["speaker_segments"]
    assert len(segments) == 3
    assert segments[0]["speaker"] == "Teacher"
    assert segments[1]["speaker"] == "Student"
    assert segments[2]["speaker"] == "Teacher"


# 17. Existing numbers and formulas still work
def test_existing_numbers_and_formulas_still_work():
    provider = HeuristicAIProvider()
    raw = (
        "The experiment was conducted at 25\u00b0C with 10 kg of material. "
        "The model accuracy reached 95 percent, and gravity was measured at 9.81 m/s\u00b2 with 10 students. "
        "Force equals mass times acceleration."
    )
    result = asyncio.run(provider.structure_transcript(raw))

    numbers = result["numbers"]
    assert "95%" in numbers
    assert any("10 kg" in n for n in numbers)
    assert any("25\u00b0C" in n for n in numbers)
    assert any("9.81 m/s\u00b2" in n for n in numbers)
    assert any("10 students" in n for n in numbers)
    assert "F = ma" in result["formulas"]


# 18. Dynamic current topic tracking and transitions
def test_step6_current_topic_tracking_and_transitions():
    provider = HeuristicAIProvider()

    # Initial topic
    initial_text = "Today we will learn supervised learning. It uses labeled datasets to train models."
    result1 = asyncio.run(provider.structure_transcript(initial_text))
    assert result1["topic"] == "Supervised Learning"
    assert len(result1["topic_history"]) == 1
    assert result1["topic_history"][0]["topic"] == "Supervised Learning"

    # Lecture progression with topic transition
    transition_text = (
        "Today we will learn supervised learning. Now let's move to classification. "
        "Classification predicts discrete classes. Next we will discuss regression."
    )
    result2 = asyncio.run(provider.structure_transcript(transition_text))
    assert result2["topic"] == "Regression"
    history_topics = [h["topic"] for h in result2["topic_history"]]
    assert history_topics == ["Supervised Learning", "Classification", "Regression"]


# 19. Topic history preservation and null timestamps
def test_step6_topic_history_preservation():
    provider = HeuristicAIProvider()
    raw = (
        "Today we are going to study neural networks. "
        "Moving on to backpropagation algorithm. "
        "Next we will discuss gradient descent."
    )
    result = asyncio.run(provider.structure_transcript(raw))
    history = result["topic_history"]
    assert len(history) == 3
    for segment in history:
        assert isinstance(segment["topic"], str)
        assert segment["timestamp"] is None  # Does not invent timestamps


# 20. Important point extraction with emphasis phrases
def test_step6_important_point_extraction():
    provider = HeuristicAIProvider()
    raw = (
        "Today we study machine learning. "
        "Remember that classification predicts discrete categories. "
        "We also spoke about different algorithms yesterday. "
        "Keep in mind that regression predicts continuous values. "
        "Most importantly, data cleanliness directly impacts model performance."
    )
    result = asyncio.run(provider.structure_transcript(raw))
    points = result["important_points"]
    assert len(points) >= 2
    assert any("classification predicts discrete categories" in p.lower() for p in points)
    assert any("regression predicts continuous values" in p.lower() for p in points)
    # General statement without emphasis should not be in important_points
    assert not any("yesterday" in p.lower() for p in points)


# 21. Explicit definition extraction without hallucination
def test_step6_definition_extraction():
    provider = HeuristicAIProvider()
    raw = (
        "Today we study computer science algorithms. "
        "An algorithm is a step-by-step procedure for solving a problem. "
        "Supervised learning refers to training a model using labeled dataset examples."
    )
    result = asyncio.run(provider.structure_transcript(raw))
    definitions = result["definitions"]
    assert len(definitions) >= 1
    term_names = [d["term"] for d in definitions]
    assert "Algorithm" in term_names
    algo_def = next(d for d in definitions if d["term"] == "Algorithm")
    assert "step-by-step procedure" in algo_def["definition"].lower()


# 22. Educational example extraction
def test_step6_example_extraction():
    provider = HeuristicAIProvider()
    raw = (
        "We are covering machine learning applications. "
        "For example, spam detection is a classification problem. "
        "An example of regression is predicting house prices."
    )
    result = asyncio.run(provider.structure_transcript(raw))
    examples = result["examples"]
    assert len(examples) >= 2
    concepts = [ex["concept"].lower() for ex in examples]
    assert "classification" in concepts
    assert "regression" in concepts
    spam_ex = next(ex for ex in examples if ex["concept"].lower() == "classification")
    assert "spam detection" in spam_ex["example"].lower()


# 23. Key review moments extraction with categories
def test_step6_important_moments_extraction():
    provider = HeuristicAIProvider()
    raw = (
        "Today we will learn physics. "
        "An algorithm is a step-by-step procedure for solving a problem. "
        "Force equals mass times acceleration. "
        "Remember that classification predicts discrete categories. "
        "For example, spam detection is a classification problem. "
        "Be careful not to confuse training data with test data."
    )
    result = asyncio.run(provider.structure_transcript(raw))
    moments = result["important_moments"]
    assert len(moments) >= 4
    types = {m["type"] for m in moments}
    assert "definition" in types
    assert "formula" in types
    assert "important_point" in types
    assert "example" in types
    assert "warning" in types
    for m in moments:
        assert m["timestamp"] is None


# 24. Full response schema via public API
def test_step6_full_response_schema_via_api(client):
    session = client.post("/api/sessions").json()
    session_id = session["session_id"]

    client.post(
        f"/api/sessions/{session_id}/transcript",
        json={"text": "Today we will learn supervised learning. An algorithm is a step-by-step procedure for solving a problem."},
    )
    client.post(
        f"/api/sessions/{session_id}/transcript",
        json={"text": "Now let's move to classification. Remember that classification predicts discrete categories. For example, spam detection is a classification problem. F = ma."},
    )

    response = client.post(f"/api/sessions/{session_id}/structure")
    assert response.status_code == 200
    data = response.json()

    # All 13 fields present in the response
    expected_fields = [
        "clean_text", "topic", "key_points", "concepts", "technical_terms",
        "numbers", "formulas", "speaker_segments", "topic_history",
        "important_points", "definitions", "examples", "important_moments"
    ]
    for field in expected_fields:
        assert field in data, f"Missing field: {field}"

    assert data["topic"] == "Classification"
    assert len(data["topic_history"]) == 2
    assert len(data["important_points"]) >= 1
    assert len(data["definitions"]) >= 1
    assert len(data["examples"]) >= 1
    assert len(data["important_moments"]) >= 1


# 25. Step 6 session isolation
def test_step6_session_isolation(client):
    # Session 1: Machine Learning
    s1 = client.post("/api/sessions").json()["session_id"]
    client.post(
        f"/api/sessions/{s1}/transcript",
        json={"text": "Today we will learn supervised learning. An algorithm is a step-by-step procedure for solving a problem. For example, spam detection is a classification problem."},
    )

    # Session 2: Physics
    s2 = client.post("/api/sessions").json()["session_id"]
    client.post(
        f"/api/sessions/{s2}/transcript",
        json={"text": "Today we will learn thermodynamics. Temperature is a measure of average kinetic energy. Force equals mass times acceleration."},
    )

    r1 = client.post(f"/api/sessions/{s1}/structure").json()
    r2 = client.post(f"/api/sessions/{s2}/structure").json()

    # Verify session 1 contains only ML intelligence
    assert "Supervised Learning" in r1["topic_history"][0]["topic"]
    assert any(d["term"] == "Algorithm" for d in r1["definitions"])
    assert not any("thermodynamics" in h["topic"].lower() for h in r1["topic_history"])

    # Verify session 2 contains only Physics intelligence
    assert "Thermodynamics" in r2["topic_history"][0]["topic"]
    assert any(d["term"] == "Temperature" for d in r2["definitions"])
    assert not any("algorithm" in d["term"].lower() for d in r2["definitions"])


# 26. Heuristic fallback offline operation
def test_step6_heuristic_fallback_offline():
    provider = HeuristicAIProvider()
    lecture = (
        "Today we will learn database systems. "
        "A primary key is a unique identifier for a database record. "
        "Remember that primary keys cannot contain null values. "
        "For example, student id is a primary key application. "
        "Be careful not to delete tables without a backup."
    )
    result = asyncio.run(provider.structure_transcript(lecture))

    assert result["topic"] == "Database Systems"
    assert len(result["topic_history"]) == 1
    assert len(result["important_points"]) >= 1
    assert any("primary key" in d["term"].lower() for d in result["definitions"])
    assert len(result["examples"]) >= 1
    assert len(result["important_moments"]) >= 3


# ==============================================================================
# PERSON 1 - STEP 7: ADVANCED LECTURE ASSISTANT TESTS
# ==============================================================================

# 27. Q&A without conversation_id creates conversation and returns conversation_id
def test_step7_qa_without_conversation_id_creates_conversation(client):
    session = client.post("/api/sessions").json()
    session_id = session["session_id"]
    client.post(
        f"/api/sessions/{session_id}/transcript",
        json={"text": "Supervised learning uses labelled training data for prediction."},
    )

    res = client.post(
        f"/api/sessions/{session_id}/qa",
        json={"question": "What is supervised learning?"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "conversation_id" in data
    assert data["conversation_id"].startswith("conv_")
    assert data["lecture_grounded"] is True


# 28. Q&A with existing conversation_id continues conversation and returns same conversation_id
def test_step7_qa_with_existing_conversation_id_continues_conversation(client):
    session = client.post("/api/sessions").json()
    session_id = session["session_id"]
    client.post(
        f"/api/sessions/{session_id}/transcript",
        json={"text": "Supervised learning uses labelled training data. For example, spam filtering is a classification task."},
    )

    # First turn
    res1 = client.post(
        f"/api/sessions/{session_id}/qa",
        json={"question": "What is supervised learning?"},
    )
    assert res1.status_code == 200
    conv_id = res1.json()["conversation_id"]

    # Second turn with conversation_id
    res2 = client.post(
        f"/api/sessions/{session_id}/qa",
        json={"question": "Give an example.", "conversation_id": conv_id},
    )
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["conversation_id"] == conv_id
    assert data2["lecture_grounded"] is True
    assert "spam" in data2["answer"].lower()


# 29. Follow-up receives previous context ("Explain that simply")
def test_step7_follow_up_simplification_receives_previous_context(client):
    session = client.post("/api/sessions").json()
    session_id = session["session_id"]
    client.post(
        f"/api/sessions/{session_id}/transcript",
        json={"text": "Classification predicts discrete categories based on labelled features."},
    )

    res1 = client.post(
        f"/api/sessions/{session_id}/qa",
        json={"question": "What is classification?"},
    )
    conv_id = res1.json()["conversation_id"]

    res2 = client.post(
        f"/api/sessions/{session_id}/qa",
        json={"question": "Explain that simply.", "conversation_id": conv_id},
    )
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["lecture_grounded"] is True
    assert "predict" in data2["answer"].lower() or "categories" in data2["answer"].lower()


# 30. Follow-up for formulas ("What is the formula?")
def test_step7_follow_up_formula_receives_previous_context(client):
    session = client.post("/api/sessions").json()
    session_id = session["session_id"]
    client.post(
        f"/api/sessions/{session_id}/transcript",
        json={"text": "Force is related to acceleration. F = ma is the equation of motion."},
    )

    res1 = client.post(
        f"/api/sessions/{session_id}/qa",
        json={"question": "What did the teacher say about force?"},
    )
    conv_id = res1.json()["conversation_id"]

    res2 = client.post(
        f"/api/sessions/{session_id}/qa",
        json={"question": "What is the formula?", "conversation_id": conv_id},
    )
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["lecture_grounded"] is True
    assert "F = ma" in data2["answer"]


# 31. Follow-up ordinal reference ("Explain the second one")
def test_step7_follow_up_ordinal_receives_previous_context(client):
    session = client.post("/api/sessions").json()
    session_id = session["session_id"]
    client.post(
        f"/api/sessions/{session_id}/transcript",
        json={"text": "We covered two topics: Regression and Classification. Classification predicts discrete categories."},
    )

    res1 = client.post(
        f"/api/sessions/{session_id}/qa",
        json={"question": "What topics did we cover?"},
    )
    conv_id = res1.json()["conversation_id"]

    res2 = client.post(
        f"/api/sessions/{session_id}/qa",
        json={"question": "Explain the second one.", "conversation_id": conv_id},
    )
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["lecture_grounded"] is True
    assert "classification" in data2["answer"].lower() or "discrete" in data2["answer"].lower()


# 32. Conversation belongs to correct session and can be retrieved
def test_step7_conversation_belongs_to_correct_session(client):
    session = client.post("/api/sessions").json()
    session_id = session["session_id"]
    client.post(
        f"/api/sessions/{session_id}/transcript",
        json={"text": "Supervised learning uses labelled training data."},
    )

    res = client.post(
        f"/api/sessions/{session_id}/qa",
        json={"question": "What is supervised learning?"},
    )
    conv_id = res.json()["conversation_id"]

    # Retrieve conversation detail
    detail = client.get(f"/api/sessions/{session_id}/conversations/{conv_id}")
    assert detail.status_code == 200
    data = detail.json()
    assert data["id"] == conv_id
    assert data["session_id"] == session_id
    assert len(data["messages"]) == 2
    assert data["messages"][0]["role"] == "user"
    assert data["messages"][0]["content"] == "What is supervised learning?"
    assert data["messages"][1]["role"] == "assistant"
    assert data["messages"][1]["lecture_grounded"] is True


# 33. Strict Session Isolation: Cross-session conversation access rejected with 404
def test_step7_cross_session_conversation_access_rejected_404(client):
    # Session A
    session_a = client.post("/api/sessions").json()["session_id"]
    client.post(
        f"/api/sessions/{session_a}/transcript",
        json={"text": "Session A lecture on neural networks."},
    )
    res_a = client.post(
        f"/api/sessions/{session_a}/qa",
        json={"question": "What is this lecture on?"},
    )
    conv_a = res_a.json()["conversation_id"]

    # Session B
    session_b = client.post("/api/sessions").json()["session_id"]
    client.post(
        f"/api/sessions/{session_b}/transcript",
        json={"text": "Session B lecture on relational databases."},
    )

    # Attempt to continue Session A's conversation from Session B
    res_tamper = client.post(
        f"/api/sessions/{session_b}/qa",
        json={"question": "Tell me more.", "conversation_id": conv_a},
    )
    assert res_tamper.status_code == 404
    assert "not found for this lecture session" in res_tamper.json()["detail"].lower()

    # Attempt to read Session A's conversation from Session B
    res_read = client.get(f"/api/sessions/{session_b}/conversations/{conv_a}")
    assert res_read.status_code == 404


# 34. Strict Session Isolation: Transcript from Session A cannot appear in Session B answers
def test_step7_session_isolation_transcript_leakage_prevented(client):
    session_a = client.post("/api/sessions").json()["session_id"]
    client.post(
        f"/api/sessions/{session_a}/transcript",
        json={"text": "Supervised learning uses labelled training data."},
    )

    session_b = client.post("/api/sessions").json()["session_id"]
    client.post(
        f"/api/sessions/{session_b}/transcript",
        json={"text": "Relational databases use SQL and foreign keys."},
    )

    # Question about ML asked in Session B must be rejected as ungrounded
    res_b = client.post(
        f"/api/sessions/{session_b}/qa",
        json={"question": "What does supervised learning use?"},
    )
    assert res_b.status_code == 200
    data_b = res_b.json()
    assert data_b["lecture_grounded"] is False
    assert "not covered" in data_b["answer"].lower()
    assert len(data_b["sources"]) == 0


# 35. Unsupported or outside-of-lecture questions return lecture_grounded=False, sources=[]
def test_step7_unsupported_or_outside_questions_not_grounded(client):
    session = client.post("/api/sessions").json()
    session_id = session["session_id"]
    client.post(
        f"/api/sessions/{session_id}/transcript",
        json={"text": "Today we discuss Newtonian mechanics and gravity."},
    )

    res = client.post(
        f"/api/sessions/{session_id}/qa",
        json={"question": "What is the capital of France?"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["lecture_grounded"] is False
    assert data["sources"] == []
    assert "not covered" in data["answer"].lower()


# 36. Explicit outside request rejected
def test_step7_explicit_outside_request_rejected(client):
    session = client.post("/api/sessions").json()
    session_id = session["session_id"]
    client.post(
        f"/api/sessions/{session_id}/transcript",
        json={"text": "Today we discuss Newtonian mechanics and gravity."},
    )

    res = client.post(
        f"/api/sessions/{session_id}/qa",
        json={"question": "What did the teacher say that was outside the lecture?"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["lecture_grounded"] is False
    assert data["sources"] == []


# 37. Creating an empty conversation explicitly via POST /sessions/{id}/conversations
def test_step7_create_conversation_endpoint(client):
    session = client.post("/api/sessions").json()
    session_id = session["session_id"]

    res = client.post(f"/api/sessions/{session_id}/conversations")
    assert res.status_code == 201
    data = res.json()
    assert "id" in data
    assert data["session_id"] == session_id
    assert data["messages"] == []


# 38. Heuristic provider offline multi-turn verification
def test_step7_heuristic_multiturn_offline():
    provider = HeuristicAIProvider()
    lecture = "Supervised learning uses labelled training data. For example, spam detection is a classification problem. F = ma is the force formula."

    # Turn 1
    t1 = asyncio.run(provider.answer_question(
        question="What is supervised learning?",
        lecture_text=lecture,
    ))
    assert t1["lecture_grounded"] is True

    history = [
        {"role": "user", "content": "What is supervised learning?"},
        {"role": "assistant", "content": t1["answer"]},
    ]

    # Turn 2: simplification
    t2 = asyncio.run(provider.answer_question(
        question="Explain that simply.",
        lecture_text=lecture,
        conversation_history=history,
    ))
    assert t2["lecture_grounded"] is True
    assert "training data" in t2["answer"].lower()

    # Turn 3: example
    t3 = asyncio.run(provider.answer_question(
        question="Give an example.",
        lecture_text=lecture,
        conversation_history=history,
    ))
    assert t3["lecture_grounded"] is True
    assert "spam" in t3["answer"].lower()

