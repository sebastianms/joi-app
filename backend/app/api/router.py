from app.api.endpoints import chat, collections, connections, widgets
from fastapi import APIRouter

api_router = APIRouter()
api_router.include_router(connections.router, prefix="/connections", tags=["connections"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(widgets.router, prefix="/widgets", tags=["widgets"])
api_router.include_router(collections.router, prefix="/collections", tags=["collections"])
