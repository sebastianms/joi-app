from __future__ import annotations

from rapidfuzz import fuzz, process

from app.models.chat import WidgetSummary
from app.repositories.widget_repository import WidgetRepository

_SCORE_CUTOFF = 55
_MAX_CANDIDATES = 5


class WidgetRecoveryService:
    def __init__(self, widget_repo: WidgetRepository) -> None:
        self._repo = widget_repo

    async def find(self, session_id: str, name_query: str) -> tuple[WidgetSummary | None, list[WidgetSummary]]:
        saved = await self._repo.list_saved(session_id)
        if not saved:
            return None, []
        names = [w.display_name or w.id for w in saved]
        matches = process.extract(
            name_query,
            names,
            scorer=fuzz.WRatio,
            score_cutoff=_SCORE_CUTOFF,
            limit=_MAX_CANDIDATES,
        )
        summaries = [
            WidgetSummary(id=saved[idx].id, display_name=saved[idx].display_name or saved[idx].id)
            for _, _, idx in matches
        ]
        if len(summaries) == 1:
            return summaries[0], []
        return None, summaries
