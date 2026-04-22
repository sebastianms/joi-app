from fastapi import APIRouter, Depends, status

from app.models.chat import ChatRequest, ChatResponse
from app.services.chat_manager import ChatManagerService
from app.services.llm_gateway import LiteLLMGateway
from app.services.triage_engine import TriageEngineService

router = APIRouter()

_chat_manager_singleton = ChatManagerService(
    triage=TriageEngineService(),
    llm=LiteLLMGateway(),
)


def get_chat_manager() -> ChatManagerService:
    """Provide the shared ChatManagerService instance (preserves session history)."""
    return _chat_manager_singleton


@router.post("/messages", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def send_message(
    request: ChatRequest,
    manager: ChatManagerService = Depends(get_chat_manager),
) -> ChatResponse:
    """Receive a user message, classify intent via triage, and return a response."""
    return manager.handle(request)