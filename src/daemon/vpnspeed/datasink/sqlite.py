import aiosqlite
import dataclasses
from datetime import date, datetime
from pathlib import Path
from typing import Tuple, Set
from vpnspeed.model import *
from vpnspeed.utils import clean_dict
from .dynamic import dynamic_backup
from .interfaces import DataBackup


@dynamic_backup
class SQLite(DataBackup):

    NAME = "sqlite"

    _db: aiosqlite.Connection

    @classmethod
    def get_name(cls) -> str:
        return cls.NAME

    @staticmethod
    def _fields(cls: type) -> List[str]:
        return [field.name for field in dataclasses.fields(cls)]

    async def _create_table(
        self, table_name: str, from_obj: type, foreign_table: str, unique: bool
    ):
        fields = ", ".join(self._fields(from_obj))

        foreign_key_format = " INTEGER NOT NULL, FOREIGN KEY ({}) REFERENCES {} (rowid)"
        unique_format = ", UNIQUE({})"

        if foreign_table:
            fields += ", " + foreign_table + "_id"
            foreign_key_format = foreign_key_format.format(
                foreign_table + "_id", foreign_table
            )

        sql_create_table = "CREATE TABLE IF NOT EXISTS {}({}{})".format(
            table_name,
            fields + foreign_key_format if foreign_table else fields,
            unique_format.format(fields) if unique else "",
        )
        cursor = await self._db.execute(sql_create_table)
        await cursor.close()

    async def start(self, url: str, params: dict):
        if not url or url != ":memory:" and not Path(url).is_absolute():
            raise ValueError("An absolute path to sqlite database is required")

        conn = aiosqlite.connect(url)
        conn.daemon = True

        self._db = await conn
        self._db.row_factory = aiosqlite.Row

        await self._create_table("probe", Probe, None, True)
        await self._create_table("test_group", TestGroup, "probe", True)
        await self._create_table("test_case", TestCase, "test_group", True)
        await self._create_table("test_run", TestRun, "test_case", False)

    async def stop(self):
        await self._db.close()

    def _format_filters(self, values: dict) -> str:
        filters = []
        for key, value in values.items():
            f = (
                key
                + "="
                + ("'{}'".format(value) if isinstance(value, str) else str(value))
            )
            filters.append(f)
        return " AND ".join(filters).replace("None", "''")

    async def _insert_row(self, table_name: str, obj, additional_fields: dict) -> int:
        obj_fields = obj.__dict__
        types = {field.name: field.type for field in dataclasses.fields(obj)}

        def adapt(k, v):
            t = types[k]

            if isinstance(v, (datetime, date)):
                return v.isoformat()
            if v is None:  # Map None to default value for propper uniqueness
                if issubclass(t, (int, float)):
                    return 0
                return ""
            return v

        obj_fields = {k: adapt(k, v) for k, v in obj_fields.items()}

        for key, value in additional_fields.items():
            obj_fields[key] = value

        sql_insert = "INSERT OR IGNORE INTO {} ({}) VALUES({})".format(
            table_name,
            ", ".join(obj_fields.keys()),
            ", ".join("?" for _ in range(len(obj_fields))),
        )

        async with self._db.execute(sql_insert, list(obj_fields.values())) as cursor:
            if not cursor.rowcount:
                sql_select = "SELECT rowid FROM {} WHERE {}".format(
                    table_name, self._format_filters(obj_fields)
                )
                cursor = await cursor.execute(sql_select)
                row = await cursor.fetchone()
                return row["rowid"]
            return cursor.lastrowid

    async def send(self, probe: Probe, group: TestGroup, case: TestCase, run: TestRun):
        probe_id = await self._insert_row("probe", probe, {})
        group_id = await self._insert_row("test_group", group, {"probe_id": probe_id})
        case_id = await self._insert_row("test_case", case, {"test_group_id": group_id})
        await self._insert_row("test_run", run, {"test_case_id": case_id})
        await self._db.commit()

    async def retrieve(
        self, *, group: TestGroup = None, start: date = None, end: date = None
    ) -> List[dict]:
        sql_select = (
            "SELECT "
            + ", ".join(
                f'p.{field} as "probe_{field}"' for field in self._fields(Probe)
            )
            + ", "
            + ", ".join(
                f'g.{field} as "group_{field}"' for field in self._fields(TestGroup)
            )
            + ", "
            + ", ".join(
                f'c.{field} as "case_{field}"' for field in self._fields(TestCase)
            )
            + ", "
            + ", ".join(
                f'r.{field} as "run_{field}"' for field in self._fields(TestRun)
            )
            + " "
            + "FROM probe AS p "
            + "JOIN test_group AS g ON g.probe_id = p.rowid "
            + "JOIN test_case  AS c ON c.test_group_id = g.rowid "
            + "JOIN test_run   AS r ON r.test_case_id = c.rowid "
        )

        where = []
        if group:
            where.append(
                " AND ".join(
                    f'g.{k} = "{v}"' for k, v in group.__dict__.items() if v is not None
                )
            )
        if start:
            where.append(f'date(r.timestamp) >= date("{start.isoformat()}")')
        if end:
            where.append(f'date(r.timestamp) <= date("{end.isoformat()}")')
        if len(where) > 0:
            sql_select += "WHERE " + " AND ".join(where)

        return self._filter_rows(await self._db.execute_fetchall(sql_select))

    async def retrieve_groups(self) -> Set[TestGroup]:
        sql_select = (
            "SELECT " + ", ".join(self._fields(TestGroup)) + " " + "FROM test_group"
        )
        groups = self._filter_rows(await self._db.execute_fetchall(sql_select))

        return {TestGroup(**group) for group in groups}

    def _filter_rows(self, rows):
        return [clean_dict(dict(row)) for row in rows]
