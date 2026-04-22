from __future__ import annotations

from typing import Final

import sqlparse
from sqlparse.sql import Statement
from sqlparse.tokens import Comment, Keyword, Whitespace


class SecurityRejectionError(Exception):
    def __init__(self, reason: str, offending_token: str | None = None) -> None:
        super().__init__(reason)
        self.reason = reason
        self.offending_token = offending_token


ALLOWED_LEADING_KEYWORDS: Final[frozenset[str]] = frozenset(
    {"SELECT", "WITH", "SHOW", "EXPLAIN"}
)

FORBIDDEN_KEYWORDS: Final[frozenset[str]] = frozenset(
    {
        "INSERT",
        "UPDATE",
        "DELETE",
        "DROP",
        "ALTER",
        "TRUNCATE",
        "CREATE",
        "GRANT",
        "REVOKE",
        "REPLACE",
        "MERGE",
        "CALL",
        "EXEC",
        "EXECUTE",
        "LOCK",
        "UNLOCK",
        "RENAME",
        "VACUUM",
        "ATTACH",
        "DETACH",
        "REINDEX",
        "ANALYZE",
    }
)

FORBIDDEN_PHRASES: Final[tuple[tuple[str, ...], ...]] = (
    ("COMMENT", "ON"),
    ("COPY",),
)

WRITABLE_PRAGMAS: Final[frozenset[str]] = frozenset(
    {
        "writable_schema",
        "journal_mode",
        "foreign_keys",
        "synchronous",
        "locking_mode",
        "secure_delete",
    }
)


class ReadOnlySqlGuard:
    @staticmethod
    def validate(sql: str) -> None:
        if sql is None or not sql.strip():
            raise SecurityRejectionError("SQL vacío no permitido")

        statements = [stmt for stmt in sqlparse.parse(sql) if _has_meaningful_tokens(stmt)]

        if len(statements) == 0:
            raise SecurityRejectionError("SQL sin sentencias ejecutables")

        if len(statements) > 1:
            raise SecurityRejectionError(
                "Múltiples sentencias no permitidas (multi-statement bloqueado)"
            )

        statement = statements[0]
        leading = _first_significant_keyword(statement)

        if leading is None:
            raise SecurityRejectionError("No se pudo identificar la sentencia inicial")

        leading_upper = leading.upper()

        if leading_upper == "PRAGMA":
            _validate_pragma(statement)
            return

        if leading_upper not in ALLOWED_LEADING_KEYWORDS:
            raise SecurityRejectionError(
                f"Sentencia inicial no permitida: {leading_upper}",
                offending_token=leading_upper,
            )

        _scan_forbidden_tokens(statement)


def _has_meaningful_tokens(statement: Statement) -> bool:
    for token in statement.flatten():
        if token.ttype in (Whitespace,) or token.ttype in Comment:
            continue
        if token.value.strip() in ("", ";"):
            continue
        return True
    return False


def _first_significant_keyword(statement: Statement) -> str | None:
    for token in statement.flatten():
        if token.ttype in (Whitespace,) or token.ttype in Comment:
            continue
        value = token.value.strip()
        if not value or value == ";":
            continue
        return value
    return None


def _scan_forbidden_tokens(statement: Statement) -> None:
    keyword_sequence: list[str] = []

    for token in statement.flatten():
        if token.ttype in (Whitespace,) or token.ttype in Comment:
            continue

        value = token.value.strip()
        if not value:
            continue

        upper = value.upper()

        if token.ttype in Keyword or upper in FORBIDDEN_KEYWORDS:
            if upper in FORBIDDEN_KEYWORDS:
                raise SecurityRejectionError(
                    f"Token prohibido detectado: {upper}",
                    offending_token=upper,
                )
            keyword_sequence.append(upper)

        _check_forbidden_phrases(keyword_sequence)


def _check_forbidden_phrases(keyword_sequence: list[str]) -> None:
    for phrase in FORBIDDEN_PHRASES:
        if len(keyword_sequence) < len(phrase):
            continue
        tail = tuple(keyword_sequence[-len(phrase):])
        if tail == phrase:
            raise SecurityRejectionError(
                f"Frase prohibida detectada: {' '.join(phrase)}",
                offending_token=" ".join(phrase),
            )


def _validate_pragma(statement: Statement) -> None:
    tokens = [
        tok.value.strip()
        for tok in statement.flatten()
        if tok.ttype not in (Whitespace,)
        and tok.ttype not in Comment
        and tok.value.strip()
        and tok.value.strip() != ";"
    ]

    if len(tokens) < 2:
        raise SecurityRejectionError("PRAGMA sin nombre no permitido")

    pragma_name = tokens[1].lower()

    if pragma_name in WRITABLE_PRAGMAS:
        raise SecurityRejectionError(
            f"PRAGMA de escritura no permitido: {pragma_name}",
            offending_token=f"PRAGMA {pragma_name}",
        )

    has_assignment = any(tok in ("=",) for tok in tokens)
    if has_assignment:
        raise SecurityRejectionError(
            f"PRAGMA con asignación no permitido: {pragma_name}",
            offending_token=f"PRAGMA {pragma_name}=",
        )
