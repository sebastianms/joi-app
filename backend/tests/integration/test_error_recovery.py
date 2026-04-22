"""Integration test — session remains functional after a data agent error.

Verifies that after an extraction error (e.g. no active connection), the same
session can still handle a simple-intent message successfully (HTTP 200 with
intent_type == "simple" and no extraction payload).
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.api.endpoints.chat import get_chat_manager
from app.main import app
from app.services.chat_manager import ChatManagerService
from app.services.llm_gateway import LLMGateway
from app.services.triage_engine import TriageEngineService


class _GreetLLM(LLMGateway):
    def complete(self, history):
        return "Hola, ¿en qué puedo ayudarte?"


@pytest.fixture
def _override_chat_manager():
    fresh_manager = ChatManagerService(
        triage=TriageEngineService(),
        llm=_GreetLLM(),
    )
    app.dependency_overrides[get_chat_manager] = lambda: fresh_manager
    yield
    app.dependency_overrides.pop(get_chat_manager, None)


@pytest.mark.asyncio
async def test_session_recovers_after_no_connection_error(
    client: AsyncClient,
    _override_chat_manager,
):
    session_id = "session-recovery"

    # First request — complex intent, no active connection → extraction error
    error_response = await client.post(
        "/api/chat/messages",
        json={"session_id": session_id, "message": "dame un análisis de ventas"},
    )
    assert error_response.status_code == 200
    error_data = error_response.json()
    assert error_data["extraction"]["error"]["code"] == "NO_CONNECTION"

    # Second request — simple intent, same session → must succeed
    ok_response = await client.post(
        "/api/chat/messages",
        json={"session_id": session_id, "message": "hola"},
    )
    assert ok_response.status_code == 200
    ok_data = ok_response.json()
    assert ok_data["intent_type"] == "simple"
    assert ok_data.get("extraction") is None
