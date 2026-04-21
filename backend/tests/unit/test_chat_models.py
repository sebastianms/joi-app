import pytest
from pydantic import ValidationError
from app.models.chat import (
    Role,
    IntentType,
    Message,
    ChatRequest,
    TriageResult,
    ChatResponse
)

def test_message_model_valid():
    msg = Message(role=Role.USER, content="Hello")
    assert msg.role == Role.USER
    assert msg.content == "Hello"

def test_message_model_invalid_role():
    with pytest.raises(ValidationError):
        Message(role="invalid_role", content="Hello")

def test_chat_request_valid():
    req = ChatRequest(session_id="123", message="Test message")
    assert req.session_id == "123"
    assert req.message == "Test message"

def test_chat_request_empty_fields():
    with pytest.raises(ValidationError):
        ChatRequest(session_id="", message="Test")
        
    with pytest.raises(ValidationError):
        ChatRequest(session_id="123", message="")

def test_triage_result_valid():
    res = TriageResult(
        intent_type=IntentType.SIMPLE,
        confidence=0.9,
        matched_pattern="hello",
        suggested_route="direct"
    )
    assert res.intent_type == IntentType.SIMPLE
    assert res.confidence == 0.9

def test_triage_result_invalid_confidence():
    with pytest.raises(ValidationError):
        TriageResult(
            intent_type=IntentType.SIMPLE,
            confidence=1.5,
            suggested_route="direct"
        )
    
    with pytest.raises(ValidationError):
        TriageResult(
            intent_type=IntentType.SIMPLE,
            confidence=-0.1,
            suggested_route="direct"
        )

def test_chat_response_valid():
    resp = ChatResponse(response="Hi there!", intent_type=IntentType.SIMPLE)
    assert resp.response == "Hi there!"
    assert resp.intent_type == IntentType.SIMPLE
