from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.chat import ChatRequest, ChatResponse
from app.repositories.connection_repository import SQLiteConnectionRepository
from app.repositories.user_session_repository import UserSessionRepository
from app.repositories.widget_repository import WidgetRepository
from app.services.agents.sql_agent_adapter import SqlAgentAdapter
from app.services.chat_manager import ChatManagerService
from app.services.data_agent_service import DataAgentService
from app.services.llm_gateway import LiteLLMGateway
from app.services.triage_engine import TriageEngineService
from app.services.widget_cache.cache_service import CacheService
from app.services.widget_recovery_service import WidgetRecoveryService

router = APIRouter()

_chat_manager_singleton = ChatManagerService(
    triage=TriageEngineService(),
    llm=LiteLLMGateway(),
)
_sql_adapter_singleton = SqlAgentAdapter()


def get_chat_manager() -> ChatManagerService:
    return _chat_manager_singleton


class RequestAgents:
    """Bundles per-request agents that require DB access (keeps send_message at 3 args)."""

    def __init__(self, db: AsyncSession = Depends(get_db)) -> None:
        self.data = DataAgentService(
            connection_repo=SQLiteConnectionRepository(db),
            session_repo=UserSessionRepository(db),
            sql_adapter=_sql_adapter_singleton,
        )
        self.recovery = WidgetRecoveryService(WidgetRepository(db))
        self.cache = CacheService(db)


@router.post(
    "/messages",
    response_model=ChatResponse,
    response_model_exclude_none=True,
    status_code=status.HTTP_200_OK,
)
async def send_message(
    request: ChatRequest,
    manager: ChatManagerService = Depends(get_chat_manager),
    agents: RequestAgents = Depends(),
) -> ChatResponse:
    return await manager.handle(request, agents.data, agents.recovery, agents.cache)
