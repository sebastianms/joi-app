from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.render_mode import RenderMode, RenderModeUpdateRequest, UILibrary
from app.repositories.render_mode_repository import RenderModeRepository

router = APIRouter()


class RenderModeResponse(BaseModel):
    session_id: str
    mode: str
    ui_library: str | None


@router.get("/{session_id}", response_model=RenderModeResponse)
async def get_render_mode(session_id: str, db: AsyncSession = Depends(get_db)):
    repo = RenderModeRepository(db)
    profile = await repo.get_or_create(session_id)
    return RenderModeResponse(
        session_id=profile.session_id,
        mode=profile.mode.value,
        ui_library=profile.ui_library.value if profile.ui_library else None,
    )


@router.put("/{session_id}", response_model=RenderModeResponse)
async def update_render_mode(
    session_id: str,
    body: RenderModeUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        mode = RenderMode(body.mode)
        ui_library = UILibrary(body.ui_library) if body.ui_library else None
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    repo = RenderModeRepository(db)
    profile = await repo.update(session_id, mode, ui_library)
    return RenderModeResponse(
        session_id=profile.session_id,
        mode=profile.mode.value,
        ui_library=profile.ui_library.value if profile.ui_library else None,
    )
