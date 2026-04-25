from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.widget import SelectionSource
from app.repositories.collection_repository import CollectionRepository
from app.repositories.widget_repository import WidgetRepository

router = APIRouter()


class SaveWidgetRequest(BaseModel):
    session_id: str
    display_name: str = Field(min_length=1, max_length=120)
    collection_ids: list[str] = Field(default_factory=list)


class WidgetSaveResponse(BaseModel):
    id: str
    display_name: str
    is_saved: bool
    collection_ids: list[str]


@router.post(
    "/{widget_id}/save",
    response_model=WidgetSaveResponse,
    status_code=status.HTTP_200_OK,
)
async def save_widget(
    widget_id: str,
    body: SaveWidgetRequest,
    db: AsyncSession = Depends(get_db),
) -> WidgetSaveResponse:
    widget_repo = WidgetRepository(db)
    collection_repo = CollectionRepository(db)

    widget = await widget_repo.get(widget_id, body.session_id)
    if widget is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Widget not found")

    if widget.selection_source == SelectionSource.FALLBACK:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Fallback widgets cannot be saved",
        )

    try:
        widget = await widget_repo.mark_saved(widget, body.display_name)
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya tienes un widget guardado con el nombre '{body.display_name}'",
        )

    for cid in body.collection_ids:
        collection = await collection_repo.get(cid, body.session_id)
        if collection is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection {cid} not found",
            )
        await collection_repo.add_widget(cid, widget_id)

    final_collection_ids = await collection_repo.collection_ids_for_widget(widget_id)
    return WidgetSaveResponse(
        id=widget.id,
        display_name=widget.display_name,
        is_saved=widget.is_saved,
        collection_ids=final_collection_ids,
    )


@router.delete(
    "/{widget_id}/save",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def unsave_widget(
    widget_id: str,
    session_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    widget_repo = WidgetRepository(db)
    collection_repo = CollectionRepository(db)

    widget = await widget_repo.get(widget_id, session_id)
    if widget is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Widget not found")

    if await widget_repo.is_in_any_dashboard(widget_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Widget is used in a dashboard and cannot be unsaved",
        )

    collection_ids = await collection_repo.collection_ids_for_widget(widget_id)
    for cid in collection_ids:
        await collection_repo.remove_widget(cid, widget_id)

    await widget_repo.mark_unsaved(widget)
