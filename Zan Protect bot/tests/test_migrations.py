import hashlib
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock

import pytest

from scripts.migrate import apply


class Connection:
    def __init__(self, previous=None):
        self.execute = AsyncMock()
        self.fetchval = AsyncMock(return_value=previous)
        self.committed = False

    @asynccontextmanager
    async def transaction(self):
        yield
        self.committed = True


async def test_new_migration_records_checksum(tmp_path):
    sql = "CREATE TABLE demo(id integer);\n"
    (tmp_path / "001_test.sql").write_text(sql, encoding="utf-8")
    conn = Connection()
    await apply(conn, tmp_path)
    conn.execute.assert_any_await(sql)
    assert conn.execute.call_args.args[1:] == ("001_test.sql", hashlib.sha256(sql.encode()).hexdigest())
    assert conn.committed


async def test_existing_migration_is_not_repeated(tmp_path):
    sql = "SELECT 1;\n"
    (tmp_path / "001_test.sql").write_bytes(sql.replace("\n", "\r\n").encode())
    conn = Connection(hashlib.sha256(sql.encode()).hexdigest())
    await apply(conn, tmp_path)
    assert all(call.args[0] != sql for call in conn.execute.await_args_list)
    assert conn.committed


async def test_modified_migration_aborts(tmp_path):
    (tmp_path / "001_test.sql").write_text("SELECT 2;", encoding="utf-8")
    conn = Connection("old-checksum")
    with pytest.raises(RuntimeError, match="Applied migration changed"):
        await apply(conn, tmp_path)
    assert not conn.committed
