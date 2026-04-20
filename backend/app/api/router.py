from app.api.endpoints import connections
from fastapi import APIRouter

api_router = APIRouter()
api_router.include_router(connections.router, prefix="/connections", tags=["connections"])
