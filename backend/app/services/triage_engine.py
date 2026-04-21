import re
from app.models.chat import IntentType, TriageResult

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


class TriageEngineService:
    """Routes user messages to the appropriate processing pipeline."""

    def classify(self, message: str) -> TriageResult:
        matched = _match_simple_pattern(message)
        if matched:
            return TriageResult(
                intent_type=IntentType.SIMPLE,
                confidence=1.0,
                matched_pattern=matched,
                suggested_route="direct_response",
            )

        if _contains_complex_keyword(message):
            return TriageResult(
                intent_type=IntentType.COMPLEX,
                confidence=0.9,
                suggested_route="agent_pipeline",
            )

        return TriageResult(
            intent_type=IntentType.SIMPLE,
            confidence=0.6,
            suggested_route="direct_response",
        )
