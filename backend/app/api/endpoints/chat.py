from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.chat import ChatRequest, ChatResponse
from app.repositories.connection_repository import SQLiteConnectionRepository
from app.repositories.user_session_repository import UserSessionRepository
from app.services.agents.sql_agent_adapter import SqlAgentAdapter
from app.services.chat_manager import ChatManagerService
from app.services.data_agent_service import DataAgentService
from app.services.llm_gateway import LiteLLMGateway
from app.services.triage_engine import TriageEngineService

router = APIRouter()

_chat_manager_singleton = ChatManagerService(
    triage=TriageEngineService(),
    llm=LiteLLMGateway(),
)
_sql_adapter_singleton = SqlAgentAdapter()


def get_chat_manager() -> ChatManagerService:
    """Provide the shared ChatManagerService instance (preserves session history)."""
    return _chat_manager_singleton


def get_data_agent(db: AsyncSession = Depends(get_db)) -> DataAgentService:
    """Build a per-request DataAgentService wired to the current DB session."""
    return DataAgentService(
        connection_repo=SQLiteConnectionRepository(db),
        session_repo=UserSessionRepository(db),
        sql_adapter=_sql_adapter_singleton,
    )


@router.post("/messages", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def send_message(
    request: ChatRequest,
    manager: ChatManagerService = Depends(get_chat_manager),
    data_agent: DataAgentService = Depends(get_data_agent),
) -> ChatResponse:
    """Receive a user message, classify intent via triage, and return a response."""
    return await manager.handle(request, data_agent)
