from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def _post(messages: list) -> dict:
    resp = client.post("/chat", json={"messages": messages})
    assert resp.status_code == 200
    return resp.json()


def test_schema_compliance():
    data = _post([{"role": "user", "content": "I need an assessment"}])
    assert "reply" in data
    assert "recommendations" in data
    assert "end_of_conversation" in data
    assert isinstance(data["reply"], str)
    assert isinstance(data["recommendations"], list)
    assert isinstance(data["end_of_conversation"], bool)


def test_vague_query_no_recommendations():
    data = _post([{"role": "user", "content": "I need an assessment"}])
    assert data["recommendations"] == [], "Should not recommend on vague query"
    assert data["end_of_conversation"] is False


def test_recommendations_have_required_fields():
    data = _post([
        {"role": "user", "content": "I need to hire a Java developer"},
        {"role": "assistant", "content": "What seniority level?"},
        {"role": "user", "content": "Senior, 5 years experience"},
    ])
    for rec in data.get("recommendations", []):
        assert "name" in rec
        assert "url" in rec
        assert "test_type" in rec
        assert rec["url"].startswith("https://www.shl.com")


def test_off_topic_refused():
    data = _post([{"role": "user", "content": "What is the legal process for hiring in the US?"}])
    assert data["recommendations"] == []


def test_max_recommendations():
    data = _post([
        {"role": "user", "content": "Need assessments for a data scientist role"},
        {"role": "assistant", "content": "What level?"},
        {"role": "user", "content": "Senior"},
    ])
    assert len(data.get("recommendations", [])) <= 10


def test_turn_limit():
    messages = []
    for i in range(4):
        messages.append({"role": "user", "content": f"Question {i}"})
        messages.append({"role": "assistant", "content": f"Answer {i}"})
    data = _post(messages)
    assert len(messages) <= 8
