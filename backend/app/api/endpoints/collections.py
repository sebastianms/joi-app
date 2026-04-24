from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.repositories.collection_repository import CollectionRepository
from app.repositories.widget_repository import WidgetRepository

router = APIRouter()


class CollectionCreateRequest(BaseModel):
    session_id: str
    name: str = Field(min_length=1, max_length=120)


class CollectionRenameRequest(BaseModel):
    session_id: str
    name: str = Field(min_length=1, max_length=120)


class CollectionWidgetsBulkRequest(BaseModel):
    session_id: str
    widget_ids: list[str]


class CollectionResponse(BaseModel):
    id: str
    session_id: str
    name: str


class WidgetInCollectionResponse(BaseModel):
    id: str
    display_name: str
    is_saved: bool


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


@router.patch(
    "/{collection_id}",
    response_model=CollectionResponse,
)
async def rename_collection(
    collection_id: str,
    body: CollectionRenameRequest,
    db: AsyncSession = Depends(get_db),
) -> CollectionResponse:
    repo = CollectionRepository(db)
    try:
        collection = await repo.update_name(collection_id, body.session_id, body.name)
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A collection with this name already exists in the session",
        )
    if collection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found")
    return CollectionResponse(
        id=collection.id,
        session_id=collection.session_id,
        name=collection.name,
    )


@router.delete(
    "/{collection_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_collection(
    collection_id: str,
    session_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    repo = CollectionRepository(db)
    deleted = await repo.delete(collection_id, session_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found")


@router.get(
    "/{collection_id}/widgets",
    response_model=list[WidgetInCollectionResponse],
)
async def list_collection_widgets(
    collection_id: str,
    session_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[WidgetInCollectionResponse]:
    collection_repo = CollectionRepository(db)
    collection = await collection_repo.get(collection_id, session_id)
    if collection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found")
    widget_ids = await collection_repo.list_widget_ids(collection_id)
    widget_repo = WidgetRepository(db)
    widgets = []
    for wid in widget_ids:
        widget = await widget_repo.get(wid, session_id)
        if widget is not None:
            widgets.append(
                WidgetInCollectionResponse(
                    id=widget.id,
                    display_name=widget.display_name or widget.id,
                    is_saved=widget.is_saved,
                )
            )
    return widgets


@router.post(
    "/{collection_id}/widgets",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def bulk_add_widgets(
    collection_id: str,
    body: CollectionWidgetsBulkRequest,
    db: AsyncSession = Depends(get_db),
) -> None:
    repo = CollectionRepository(db)
    collection = await repo.get(collection_id, body.session_id)
    if collection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found")
    for widget_id in body.widget_ids:
        await repo.add_widget(collection_id, widget_id)


@router.delete(
    "/{collection_id}/widgets/{widget_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_widget_from_collection(
    collection_id: str,
    widget_id: str,
    session_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    repo = CollectionRepository(db)
    collection = await repo.get(collection_id, session_id)
    if collection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found")
    await repo.remove_widget(collection_id, widget_id)
