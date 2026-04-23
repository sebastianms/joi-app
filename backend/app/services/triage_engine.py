import re
from app.models.chat import IntentType, TriageResult
from app.models.widget import WidgetType

_SIMPLE_PATTERNS: list[str] = [
    r"^\s*(hola|hi|hello|hey)\b",
    r"^\s*(gracias|thanks|thank you)\b",
    r"^\s*(adiós|adios|bye|chau|goodbye)\b",
    r"^\s*(ok|okay|perfecto|genial|entendido|listo)\b",
    r"^\s*(sí|si|no|nope|claro)\b",
    r"^\s*(como estás|how are you|qué tal|how's it going)",
]

_COMPLEX_KEYWORDS: list[str] = [
    "muestra", "muéstrame", "show", "dame", "give me",
    "gráfica", "grafica", "gráfico", "chart", "table", "tabla",
    "lista", "list", "visualiza", "visualize",
    "consulta", "query", "datos", "data", "reporte", "report",
    "cuántos", "cuantos", "cuántas", "cuantas", "how many", "how much",
    "cuál", "cual", "which", "compara", "compare",
    "top", "ventas", "sales", "promedio", "average", "total",
    "dashboard", "widget", "genera", "generate", "crea", "create",
]

# R10 — widget preference patterns (FR-006a). One entry per widget type.
# If two or more types match, no preference is assumed (conservative).
_WIDGET_PREFERENCE_PATTERNS: list[tuple[re.Pattern[str], WidgetType]] = [
    (re.compile(r"\b(barra(s)?|gr[aá]fico de barras|bar chart|bar graph)\b", re.IGNORECASE), WidgetType.BAR_CHART),
    (re.compile(r"\b(tabla|table)\b", re.IGNORECASE), WidgetType.TABLE),
    (re.compile(r"\b(l[ií]nea(s)?|line chart|serie(s)? temporal(es)?|gr[aá]fico de l[ií]neas)\b", re.IGNORECASE), WidgetType.LINE_CHART),
    (re.compile(r"\b(pastel|torta|pie( chart)?|donut)\b", re.IGNORECASE), WidgetType.PIE_CHART),
    (re.compile(r"\b(kpi|indicador(es)?|m[eé]trica(s)?)\b", re.IGNORECASE), WidgetType.KPI),
    (re.compile(r"\b(scatter( plot)?|dispersi[oó]n|puntos)\b", re.IGNORECASE), WidgetType.SCATTER_PLOT),
    (re.compile(r"\b(heatmap|mapa de calor)\b", re.IGNORECASE), WidgetType.HEATMAP),
    (re.compile(r"\b([aá]rea( chart)?|gr[aá]fico de [aá]rea)\b", re.IGNORECASE), WidgetType.AREA_CHART),
]

_COMPILED_SIMPLE = [re.compile(p, re.IGNORECASE) for p in _SIMPLE_PATTERNS]


def _match_simple_pattern(text: str) -> str | None:
    for pattern in _COMPILED_SIMPLE:
        m = pattern.search(text)
        if m:
            return m.group(0).strip()
    return None


def _contains_complex_keyword(text: str) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in _COMPLEX_KEYWORDS)


def _detect_widget_preference(text: str) -> WidgetType | None:
    """Return the widget type if exactly one preference pattern matches (R10).

    Conservative: two or more matches → no preference assumed.
    """
    matched: list[WidgetType] = [
        wtype for pattern, wtype in _WIDGET_PREFERENCE_PATTERNS
        if pattern.search(text)
    ]
    return matched[0] if len(matched) == 1 else None


class TriageEngineService:
    """Routes user messages to the appropriate processing pipeline."""

    def classify(self, message: str, has_prior_extraction: bool = False) -> TriageResult:
        matched = _match_simple_pattern(message)
        if matched:
            return TriageResult(
                intent_type=IntentType.SIMPLE,
                confidence=1.0,
                matched_pattern=matched,
                suggested_route="direct_response",
            )

        if _contains_complex_keyword(message):
            preferred = _detect_widget_preference(message)
            return TriageResult(
                intent_type=IntentType.COMPLEX,
                confidence=0.9,
                suggested_route="agent_pipeline",
                preferred_widget_type=preferred,
            )

        # Second pass: widget preference on a message that references a prior extraction
        # (e.g. "muéstramelo como tabla") without explicit data keywords.
        if has_prior_extraction:
            preferred = _detect_widget_preference(message)
            if preferred is not None:
                return TriageResult(
                    intent_type=IntentType.COMPLEX,
                    confidence=0.9,
                    suggested_route="widget_preference",
                    preferred_widget_type=preferred,
                )

        return TriageResult(
            intent_type=IntentType.SIMPLE,
            confidence=0.6,
            suggested_route="direct_response",
        )
