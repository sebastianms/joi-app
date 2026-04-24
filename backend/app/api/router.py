from app.api.endpoints import chat, collections, connections, dashboards, health, vector_store, widget_cache, widgets
from fastapi import APIRouter

api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(connections.router, prefix="/connections", tags=["connections"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(widgets.router, prefix="/widgets", tags=["widgets"])
api_router.include_router(collections.router, prefix="/collections", tags=["collections"])
api_router.include_router(dashboards.router, prefix="/dashboards", tags=["dashboards"])
api_router.include_router(widget_cache.router, prefix="/widget-cache", tags=["widget-cache"])
api_router.include_router(vector_store.router, prefix="/vector-store", tags=["vector-store"])
