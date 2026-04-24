from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.repositories.dashboard_repository import DashboardRepository
from app.repositories.widget_repository import WidgetRepository

router = APIRouter()


class DashboardCreateRequest(BaseModel):
    session_id: str
    name: str = Field(min_length=1, max_length=120)


class DashboardRenameRequest(BaseModel):
    session_id: str
    name: str = Field(min_length=1, max_length=120)


class DashboardItemRequest(BaseModel):
    session_id: str
    widget_id: str
    grid_x: int = Field(default=0, ge=0)
    grid_y: int = Field(default=0, ge=0)
    width: int = Field(default=4, ge=1, le=12)
    height: int = Field(default=3, ge=1)


class LayoutItemRequest(BaseModel):
    widget_id: str
    grid_x: int = Field(ge=0)
    grid_y: int = Field(ge=0)
    width: int = Field(ge=1, le=12)
    height: int = Field(ge=1)
    z_order: int = 0


class LayoutUpdateRequest(BaseModel):
    session_id: str
    items: list[LayoutItemRequest]


class DashboardItemResponse(BaseModel):
    id: str
    widget_id: str
    display_name: str
    grid_x: int
    grid_y: int
    width: int
    height: int
    z_order: int


class DashboardResponse(BaseModel):
    id: str
    session_id: str
    name: str
    items: list[DashboardItemResponse] = []


async def _build_item_responses(
    dashboard_id: str,
    session_id: str,
    db: AsyncSession,
) -> list[DashboardItemResponse]:
    items = await DashboardRepository(db).list_items(dashboard_id)
    widget_repo = WidgetRepository(db)
    result = []
    for item in items:
        widget = await widget_repo.get(item.widget_id, session_id)
        display_name = widget.display_name if widget and widget.display_name else item.widget_id
        result.append(
            DashboardItemResponse(
                id=item.id,
                widget_id=item.widget_id,
                display_name=display_name,
                grid_x=item.grid_x,
                grid_y=item.grid_y,
                width=item.width,
                height=item.height,
                z_order=item.z_order,
            )
        )
    return result


@router.post("", response_model=DashboardResponse, status_code=status.HTTP_201_CREATED)
async def create_dashboard(
    body: DashboardCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> DashboardResponse:
    repo = DashboardRepository(db)
    try:
        dashboard = await repo.create(body.session_id, body.name)
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A dashboard with this name already exists in the session",
        )
    return DashboardResponse(id=dashboard.id, session_id=dashboard.session_id, name=dashboard.name)


@router.get("", response_model=list[DashboardResponse])
async def list_dashboards(
    session_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[DashboardResponse]:
    repo = DashboardRepository(db)
    dashboards = await repo.list_by_session(session_id)
    return [DashboardResponse(id=d.id, session_id=d.session_id, name=d.name) for d in dashboards]


@router.get("/{dashboard_id}", response_model=DashboardResponse)
async def get_dashboard(
    dashboard_id: str,
    session_id: str,
    db: AsyncSession = Depends(get_db),
) -> DashboardResponse:
    repo = DashboardRepository(db)
    dashboard = await repo.get(dashboard_id, session_id)
    if dashboard is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dashboard not found")
    items = await _build_item_responses(dashboard_id, session_id, db)
    return DashboardResponse(id=dashboard.id, session_id=dashboard.session_id, name=dashboard.name, items=items)


@router.patch("/{dashboard_id}", response_model=DashboardResponse)
async def rename_dashboard(
    dashboard_id: str,
    body: DashboardRenameRequest,
    db: AsyncSession = Depends(get_db),
) -> DashboardResponse:
    repo = DashboardRepository(db)
    try:
        dashboard = await repo.update_name(dashboard_id, body.session_id, body.name)
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A dashboard with this name already exists in the session",
        )
    if dashboard is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dashboard not found")
    return DashboardResponse(id=dashboard.id, session_id=dashboard.session_id, name=dashboard.name)


@router.delete("/{dashboard_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dashboard(
    dashboard_id: str,
    session_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    repo = DashboardRepository(db)
    deleted = await repo.delete(dashboard_id, session_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dashboard not found")


@router.patch("/{dashboard_id}/layout", status_code=status.HTTP_204_NO_CONTENT)
async def update_layout(
    dashboard_id: str,
    body: LayoutUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> None:
    repo = DashboardRepository(db)
    dashboard = await repo.get(dashboard_id, body.session_id)
    if dashboard is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dashboard not found")
    await repo.update_layout(
        dashboard_id,
        [item.model_dump() for item in body.items],
    )


@router.post("/{dashboard_id}/items", response_model=DashboardItemResponse, status_code=status.HTTP_201_CREATED)
async def add_dashboard_item(
    dashboard_id: str,
    body: DashboardItemRequest,
    db: AsyncSession = Depends(get_db),
) -> DashboardItemResponse:
    repo = DashboardRepository(db)
    dashboard = await repo.get(dashboard_id, body.session_id)
    if dashboard is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dashboard not found")
    widget_repo = WidgetRepository(db)
    widget = await widget_repo.get(body.widget_id, body.session_id)
    if widget is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Widget not found")
    try:
        item = await repo.add_item(
            dashboard_id,
            body.widget_id,
            grid_x=body.grid_x,
            grid_y=body.grid_y,
            width=body.width,
            height=body.height,
        )
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Widget is already in this dashboard",
        )
    display_name = widget.display_name or widget.id
    return DashboardItemResponse(
        id=item.id,
        widget_id=item.widget_id,
        display_name=display_name,
        grid_x=item.grid_x,
        grid_y=item.grid_y,
        width=item.width,
        height=item.height,
        z_order=item.z_order,
    )


@router.delete("/{dashboard_id}/items/{widget_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_dashboard_item(
    dashboard_id: str,
    widget_id: str,
    session_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    repo = DashboardRepository(db)
    dashboard = await repo.get(dashboard_id, session_id)
    if dashboard is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dashboard not found")
    await repo.remove_item(dashboard_id, widget_id)
