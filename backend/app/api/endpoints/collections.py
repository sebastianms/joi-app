from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.repositories.collection_repository import CollectionRepository

router = APIRouter()


class CollectionCreateRequest(BaseModel):
    session_id: str
    name: str = Field(min_length=1, max_length=120)


class CollectionResponse(BaseModel):
    id: str
    session_id: str
    name: str


@router.post(
    "",
    response_model=CollectionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_collection(
    body: CollectionCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> CollectionResponse:
    repo = CollectionRepository(db)
    try:
        collection = await repo.create(body.session_id, body.name)
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A collection with this name already exists in the session",
        )
    return CollectionResponse(
        id=collection.id,
        session_id=collection.session_id,
        name=collection.name,
    )


@router.get(
    "",
    response_model=list[CollectionResponse],
)
async def list_collections(
    session_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[CollectionResponse]:
    repo = CollectionRepository(db)
    collections = await repo.list_by_session(session_id)
    return [
        CollectionResponse(id=c.id, session_id=c.session_id, name=c.name)
        for c in collections
    ]
