import pytest

from app.services.read_only_sql_guard import (
    ReadOnlySqlGuard,
    SecurityRejectionError,
)


# --- Allowed leading statements ---

def test_allows_simple_select():
    ReadOnlySqlGuard.validate("SELECT * FROM sales")


def test_allows_select_with_subquery():
    ReadOnlySqlGuard.validate("SELECT a FROM (SELECT a FROM t) sub")


def test_allows_with_cte():
    ReadOnlySqlGuard.validate("WITH cte AS (SELECT 1) SELECT * FROM cte")


def test_allows_nested_with_cte():
    sql = "WITH a AS (SELECT 1), b AS (SELECT 2 FROM a) SELECT * FROM b"
    ReadOnlySqlGuard.validate(sql)


def test_allows_show_tables():
    ReadOnlySqlGuard.validate("SHOW TABLES")


def test_allows_explain_select():
    ReadOnlySqlGuard.validate("EXPLAIN SELECT * FROM users")


def test_allows_lowercase_select():
    ReadOnlySqlGuard.validate("select id from t")


def test_allows_select_with_leading_whitespace():
    ReadOnlySqlGuard.validate("   SELECT 1   ")


def test_allows_pragma_readonly_name():
    ReadOnlySqlGuard.validate("PRAGMA table_info(sales)")


# --- Rejected leading statements (blacklist first token) ---

@pytest.mark.parametrize(
    "sql,offending",
    [
        ("DELETE FROM sales", "DELETE"),
        ("DROP TABLE users", "DROP"),
        ("UPDATE t SET x=1", "UPDATE"),
        ("INSERT INTO t VALUES (1)", "INSERT"),
        ("ALTER TABLE t ADD c INT", "ALTER"),
        ("TRUNCATE TABLE t", "TRUNCATE"),
        ("CREATE TABLE x (a INT)", "CREATE"),
        ("GRANT ALL ON t TO u", "GRANT"),
        ("REVOKE SELECT ON t FROM u", "REVOKE"),
        ("REPLACE INTO t VALUES (1)", "REPLACE"),
        ("MERGE INTO t USING s ON t.id=s.id", "MERGE"),
        ("CALL proc()", "CALL"),
        ("EXEC sp_foo", "EXEC"),
        ("EXECUTE sp_foo", "EXECUTE"),
        ("VACUUM", "VACUUM"),
        ("ATTACH DATABASE 'x' AS b", "ATTACH"),
        ("DETACH DATABASE b", "DETACH"),
        ("REINDEX t", "REINDEX"),
        ("ANALYZE t", "ANALYZE"),
        ("RENAME TABLE t TO u", "RENAME"),
        ("LOCK TABLES t READ", "LOCK"),
        ("UNLOCK TABLES", "UNLOCK"),
        ("COMMENT ON TABLE t IS 'x'", "COMMENT"),
        ("COPY t TO stdout", "COPY"),
    ],
)
def test_rejects_forbidden_leading_keyword(sql: str, offending: str):
    with pytest.raises(SecurityRejectionError) as exc:
        ReadOnlySqlGuard.validate(sql)
    assert exc.value.offending_token == offending


# --- Multi-statement detection ---

def test_rejects_multi_statement_select_then_delete():
    with pytest.raises(SecurityRejectionError) as exc:
        ReadOnlySqlGuard.validate("SELECT 1; DELETE FROM sales")
    assert "múltiples" in exc.value.reason.lower()


def test_rejects_multi_statement_two_selects():
    with pytest.raises(SecurityRejectionError):
        ReadOnlySqlGuard.validate("SELECT 1; SELECT 2")


def test_allows_trailing_semicolon():
    ReadOnlySqlGuard.validate("SELECT 1;")


def test_allows_trailing_semicolon_and_whitespace():
    ReadOnlySqlGuard.validate("SELECT 1;   ")


# --- PRAGMA handling (SQLite) ---

@pytest.mark.parametrize(
    "sql",
    [
        "PRAGMA writable_schema=ON",
        "PRAGMA writable_schema = ON",
        "PRAGMA journal_mode=WAL",
        "PRAGMA foreign_keys=OFF",
        "PRAGMA synchronous=0",
        "PRAGMA secure_delete=OFF",
    ],
)
def test_rejects_writable_pragma(sql: str):
    with pytest.raises(SecurityRejectionError) as exc:
        ReadOnlySqlGuard.validate(sql)
    assert "pragma" in exc.value.reason.lower()


def test_rejects_pragma_with_assignment_even_on_unknown_name():
    with pytest.raises(SecurityRejectionError):
        ReadOnlySqlGuard.validate("PRAGMA cache_size=10000")


def test_rejects_pragma_without_name():
    with pytest.raises(SecurityRejectionError):
        ReadOnlySqlGuard.validate("PRAGMA")


# --- Empty and whitespace-only inputs ---

def test_rejects_empty_string():
    with pytest.raises(SecurityRejectionError):
        ReadOnlySqlGuard.validate("")


def test_rejects_whitespace_only():
    with pytest.raises(SecurityRejectionError):
        ReadOnlySqlGuard.validate("   \n\t  ")


def test_rejects_only_comments():
    with pytest.raises(SecurityRejectionError):
        ReadOnlySqlGuard.validate("-- just a comment\n/* block */")


def test_rejects_only_semicolon():
    with pytest.raises(SecurityRejectionError):
        ReadOnlySqlGuard.validate(";")


# --- Error payload shape ---

def test_security_rejection_exposes_reason_attribute():
    with pytest.raises(SecurityRejectionError) as exc:
        ReadOnlySqlGuard.validate("DROP TABLE x")
    assert exc.value.reason
    assert str(exc.value) == exc.value.reason


def test_security_rejection_exposes_offending_token_for_blacklist():
    with pytest.raises(SecurityRejectionError) as exc:
        ReadOnlySqlGuard.validate("DELETE FROM t")
    assert exc.value.offending_token == "DELETE"
