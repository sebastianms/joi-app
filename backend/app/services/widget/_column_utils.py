"""Column-shape helpers shared by type_selector and applicability.

Both modules classify `DataExtraction` columns by type and measure categorical
cardinality. Keeping the shared primitives here prevents divergence if the
type taxonomy evolves (e.g. adding new numeric subtypes).
"""

from __future__ import annotations

from app.models.extraction import ColumnDescriptor

NUMERIC_TYPES = frozenset({"integer", "float"})


def numeric_columns(columns: list[ColumnDescriptor]) -> list[ColumnDescriptor]:
    return [c for c in columns if c.type in NUMERIC_TYPES]


def datetime_columns(columns: list[ColumnDescriptor]) -> list[ColumnDescriptor]:
    return [c for c in columns if c.type == "datetime"]


def string_columns(columns: list[ColumnDescriptor]) -> list[ColumnDescriptor]:
    return [c for c in columns if c.type == "string"]


def unique_count(rows: list[dict], column: str) -> int:
    seen: set = set()
    for row in rows:
        value = row.get(column)
        if value is not None:
            seen.add(value)
    return len(seen)


def small_categoricals(
    rows: list[dict],
    columns: list[ColumnDescriptor],
    min_unique: int,
    max_unique: int,
) -> list[ColumnDescriptor]:
    return [c for c in columns if min_unique <= unique_count(rows, c.name) <= max_unique]
