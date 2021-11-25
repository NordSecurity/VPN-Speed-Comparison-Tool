import os
import unittest
from datetime import datetime, date

from utils import async_test

from vpnspeed.model import *
from vpnspeed.datasink import DataBackup, DynamicDataBackup, DynamicDataSink


PROBES = [
    Probe(
        ip="10.10.10.10",
        country="Germany",
        country_code="de",
        city="Frankfut",
        start_time=datetime(2020, 1, 1),
    ),
    Probe(
        ip="10.10.10.10",
        country="Germany",
        country_code="de",
        city="Frankfut",
        start_time=datetime(2020, 2, 1),
    ),
]

COUNTRIES = [
    ("Germany", "de"),
    ("United States of America", "us"),
    ("United Kindom", "gb"),
]

GROUPS = {cc: TestGroup(cc, cc) for _, cc in COUNTRIES}

CASES = [
    TestCase("nordvpn", "openvpn", "udp"),
    TestCase("nordvpn", "openvpn", "tcp"),
    TestCase("nordvpn", "wireguard"),
    TestCase("expressvpn", "openvpn", "udp"),
    TestCase("expressvpn", "openvpn", "tcp"),
]

RUN_FILL = {
    "ping_latency": 15.0,
    "ping_jitter": 0.1,
    "download_bandwidth": 10000000,
    "download_bytes": 100000000,
    "download_elapsed": 15000,
    "upload_bandwidth": 10000000,
    "upload_bytes": 100000000,
    "upload_elapsed": 10000,
    "isp": "ISP",
    "server_ip": "1.1.1.1",
    "server_location": "City",
    "packet_loss": 0,
}

# s RUNS [country_code][month][day]
RUNS = {
    cc: [
        [
            TestRun(
                timestamp=datetime(2020, month, day),
                server_country=c,
                server_country_code=cc,
                **RUN_FILL,
            )
            for day in range(1, 6)  # Day List
        ]
        for month in range(1, 3)
    ]  # Month List
    for c, cc in COUNTRIES  # Country Map
}


def dataset(probe, cc, case, month, day):
    return [
        PROBES[probe],
        GROUPS[cc],
        CASES[case],
        RUNS[cc][month - 1][day - 1],
    ]


def expect(probe, cc, case, month, day):
    def correct(v):
        if isinstance(v, datetime):
            return v.isoformat()
        return v

    def prefixed(p, o):
        return {f"{p}_{k}": correct(v) for k, v in o.__dict__.items()}

    return {
        k: v
        for k, v in {
            **prefixed("probe", PROBES[probe]),
            **prefixed("group", GROUPS[cc]),
            **prefixed("case", CASES[case]),
            **prefixed("run", RUNS[cc][month - 1][day - 1]),
        }.items()
        if v is not None
    }


class TestDynamicBackups(unittest.TestCase):
    @async_test
    async def test_backups(self):
        tests = {
            "sqlite": {"url": ":memory:"},
            "csv": {
                "url": os.path.join(
                    os.path.realpath(os.path.dirname(__file__)), "test.csv"
                )
            },
        }

        for test in tests.items():
            await self.single_backup_test(test)

        try:
            os.remove(tests["csv"]["url"])
        except FileNotFoundError:
            pass

    async def single_backup_test(self, test):
        self.maxDiff = None
        name, args = test
        backup = DynamicDataBackup(name)

        await backup.start(**args)

        setups = [
            [0, "de", 0, 1, 1],
            [0, "de", 1, 1, 2],
            [0, "de", 2, 1, 3],
            [0, "de", 3, 1, 4],
            [0, "de", 4, 1, 5],
            [0, "us", 0, 1, 1],
            [0, "us", 1, 1, 2],
            [0, "us", 2, 1, 3],
            [0, "us", 3, 1, 4],
            [0, "us", 4, 1, 5],
            [1, "gb", 0, 2, 1],
            [1, "gb", 1, 2, 2],
            [1, "gb", 2, 2, 3],
            [1, "gb", 3, 2, 4],
            [1, "gb", 4, 2, 5],
        ]

        def key(x):
            if x is not dict:
                return datetime(2020, 1, 1)
            return x.get("run_timestamp", datetime(2020, 1, 1))

        # Test basic data population.
        expected = []
        for setup in setups:
            await backup.send(*dataset(*setup))
            expected.append(expect(*setup))

            self.assertEqual(
                sorted(expected, key=key),
                sorted(await backup.retrieve(), key=key),
                f"{name}: Send {setup} failed.",
            )

        # Test group filtering

        # By group
        result = sorted(await backup.retrieve(group=TestGroup("de", "de")), key=key)
        expected = sorted([expect(*setup) for setup in setups[:5]], key=key)
        self.assertEqual(expected, result, f"{name}: Filter by 'de-de' failed.")

        result = sorted(await backup.retrieve(group=TestGroup("us", "us")), key=key)
        expected = sorted([expect(*setup) for setup in setups[5:10]], key=key)
        self.assertEqual(expected, result, f"{name}: Filter by 'us-us' failed.")

        result = sorted(await backup.retrieve(group=TestGroup("de", "us")), key=key)
        expected = sorted([], key=key)
        self.assertEqual(expected, result, f"{name}: Filter by 'de-us' failed.")

        # By time
        result = sorted(await backup.retrieve(start=date(2020, 2, 1)), key=key)
        expected = sorted([expect(*setup) for setup in setups[10:15]], key=key)
        self.assertEqual(expected, result, f"{name}: Filter by start=2020-2-1 failed.")

        result = sorted(await backup.retrieve(end=date(2020, 1, 5)), key=key)
        expected = sorted([expect(*setup) for setup in setups[0:10]], key=key)
        self.assertEqual(expected, result, f"{name}: Filter by end=2020-1-5 failed.")

        result = sorted(
            await backup.retrieve(start=date(2020, 2, 1), end=date(2020, 2, 3)), key=key
        )
        expected = sorted([expect(*setup) for setup in setups[10:13]], key=key)
        self.assertEqual(
            expected, result, f"{name}: Filter by start=2020-2-1 end=2020-2-3 failed."
        )

        # Full filter
        result = sorted(
            await backup.retrieve(
                group=TestGroup("us", "us"),
                start=date(2020, 1, 1),
                end=date(2020, 1, 2),
            ),
            key=key,
        )
        expected = sorted([expect(*setup) for setup in setups[5:7]], key=key)
        self.assertEqual(
            expected,
            result,
            f"{name}: Filter by start=2020-1-1 end=2020-1-2 'us-us' failed.",
        )

        # Test retrive groups
        self.assertEqual(set(GROUPS.values()), await backup.retrieve_groups())

        await backup.stop()
