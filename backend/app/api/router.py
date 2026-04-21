from app.api.endpoints import chat, connections
from fastapi import APIRouter

api_router = APIRouter()
api_router.include_router(connections.router, prefix="/connections", tags=["connections"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
