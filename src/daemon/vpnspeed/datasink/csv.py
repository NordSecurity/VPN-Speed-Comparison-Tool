import aiosqlite
import dataclasses
import pandas as pd
import numpy as np
from datetime import date, datetime
from pathlib import Path
from typing import Tuple, Set
from vpnspeed import log
from vpnspeed.model import *
from vpnspeed.utils import clean_dict
from .dynamic import dynamic_backup
from .interfaces import DataBackup


_COLUMNS = [
    f"{n}_{field.name}"
    for n, t in [
        ("probe", Probe),
        ("group", TestGroup),
        ("case", TestCase),
        ("run", TestRun),
    ]
    for field in dataclasses.fields(t)
]


def dict_to_csv(d: List[dict]):
    df = pd.DataFrame.from_records(d)
    return df.to_csv(index=False)


@dynamic_backup
class CSV(DataBackup):

    NAME = "csv"

    _base: pd.DataFrame = pd.DataFrame(columns=_COLUMNS)
    _path: str

    @classmethod
    def get_name(cls) -> str:
        return cls.NAME

    @staticmethod
    def _fields(cls: type) -> List[str]:
        return [field.name for field in dataclasses.fields(cls)]

    async def start(self, url: str, params: dict = None):
        if not Path(url).is_absolute():
            raise ValueError("An absolute path to csv is required")
        self._path = url
        try:
            self._base.to_csv(self._path, mode="x", index=False)
        except FileExistsError:
            pass

    async def stop(self):
        pass

    async def send(self, probe: Probe, group: TestGroup, case: TestCase, run: TestRun):
        def prefixed(prefix, obj) -> dict:
            return {f"{prefix}_{k}": v for k, v in obj.__dict__.items()}

        df = pd.concat(
            [
                self._base,
                pd.DataFrame(
                    {
                        **prefixed("probe", probe),
                        **prefixed("group", group),
                        **prefixed("case", case),
                        **prefixed("run", run),
                    },
                    index=[0],
                ),
            ],
            ignore_index=True,
        )

        df = df.applymap(lambda x: x.isoformat() if isinstance(x, datetime) else x)

        df.to_csv(self._path, mode="a", header=False, index=False)

    async def retrieve(
        self, *, group: TestGroup = None, start: date = None, end: date = None
    ) -> List[dict]:
        df: pd.DataFrame = pd.read_csv(self._path, keep_default_na=False)
        if group:
            for k, v in group.__dict__.items():
                if v is not None:
                    df = df[df[f"group_{k}"] == v]

        df["date"] = (
            df["run_timestamp"].apply(datetime.fromisoformat).apply(datetime.date)
        )
        if start:
            df = df[df["date"] >= start]
        if end:
            df = df[df["date"] <= end]
        del df["date"]

        return [clean_dict(d) for d in df.to_dict(orient="records")]

    async def retrieve_groups(self) -> Set[TestGroup]:
        df: pd.DataFrame = pd.read_csv(self._path, keep_default_na=False)
        df = df[[column for column in df.columns if column.startswith("group_")]]
        df = df.drop_duplicates().rename(columns=lambda x: x[6:])

        return {TestGroup(**clean_dict(data)) for data in df.to_dict(orient="records")}
