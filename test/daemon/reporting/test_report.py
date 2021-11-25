import unittest
import os
import json
import pandas as pd
import numpy as np
from pandas import DataFrame, Index
from datetime import datetime, date
from copy import deepcopy
from unittest.mock import Mock

from utils import async_test

from vpnspeed.reporting import *
from vpnspeed.model import *
from vpnspeed.datasink.csv import CSV


SAMPLE_DATASET = os.path.join(os.path.realpath(os.path.dirname(__file__)), "sample.csv")


class TestReportGenerator(unittest.TestCase):
    generator: ReportGenerator

    def setUp(self):
        self.db = CSV()
        self.generator = ReportGenerator(self.db)
        self.filter_full = ReportFilter(
            start=date(2000, 1, 1),
            end=date(2021, 1, 1),
            outliers=0,
        )

    @async_test
    async def test_make_report(self):
        await self.db.start(SAMPLE_DATASET)

        group = TestGroup("de", "de")
        report = await self.generator.make_report(group, self.filter_full)

        # Means
        expected = DataFrame(
            data=[272.0, 289.0, 428.0],
            index=Index(
                ["nordvpn-openvpn-udp", "nordvpn-openvpn-tcp", "nordvpn-ikev2"],
                name="case",
            ),
            columns=["download_speed"],
        )
        self.assertEqualDF(expected, report.averages.round(0))

        # Mean over time
        expected = DataFrame(
            data=[
                [377.0, 280.0, 260.0],
                [471.0, 297.0, 284.0],
            ],
            index=Index([date(2020, 7, 28), date(2020, 7, 29)], name=("date")),
            columns=Index(
                ["nordvpn-ikev2", "nordvpn-openvpn-tcp", "nordvpn-openvpn-udp"],
                name="case",
            ),
        )
        self.assertEqualDF(expected, report.average_over_time.round(0))

        # Runs per hour
        excepted = DataFrame(
            data=[
                [
                    3,
                    4,
                    3,
                    4,
                    3,
                    3,
                    2,
                    4,
                    4,
                    3,
                    3,
                    0,
                    0,
                    0,
                    3,
                    4,
                    3,
                    2,
                    3,
                    4,
                    3,
                    4,
                    0,
                    4,
                ],
                [
                    4,
                    3,
                    2,
                    4,
                    2,
                    3,
                    4,
                    3,
                    3,
                    3,
                    1,
                    0,
                    0,
                    0,
                    4,
                    2,
                    4,
                    3,
                    3,
                    3,
                    3,
                    2,
                    2,
                    4,
                ],
                [
                    3,
                    4,
                    3,
                    3,
                    3,
                    3,
                    3,
                    2,
                    2,
                    2,
                    2,
                    0,
                    0,
                    0,
                    3,
                    4,
                    3,
                    4,
                    2,
                    2,
                    4,
                    2,
                    3,
                    3,
                ],
            ],
            index=Index(
                ["nordvpn-ikev2", "nordvpn-openvpn-tcp", "nordvpn-openvpn-udp"],
                name="case",
            ),
            columns=Index(list(range(24)), name="hour"),
        )
        self.assertEqualDF(excepted, report.runs_by_hour)

        # Percentiles
        excepted = DataFrame(
            data=[
                [18.0, 269.0, 289.0, 303.0, 346.0],
                [0.0, 254.0, 299.0, 357.0, 447.0],
                [1.0, 371.0, 506.0, 541.0, 571.0],
                # [20.0, 270.0, 289.0, 302.0, 331.0],
                # [1.0, 371.0, 506.0, 540.0, 567.0],
                # [13.0, 257.0, 299.0, 354.0, 435.0],
            ],
            index=Index(
                ["nordvpn-openvpn-udp", "nordvpn-openvpn-tcp", "nordvpn-ikev2"],
                name="case",
            ),
            columns=Index(
                ["5th", "25th", "50th", "75th", "95th"], name="download_speed"
            ),
        )
        self.assertEqualDF(excepted, report.percentiles.round(0))

    @async_test
    async def test_return_none_report_for_empty_dataset(self):
        await self.db.start(SAMPLE_DATASET)
        self.assertIsNone(await self.generator.make_report(TestGroup("nl", "nl")))

    @async_test
    async def test_make_reports(self):
        await self.db.start(SAMPLE_DATASET)

        reports = [
            report async for report in self.generator.make_reports(self.filter_full)
        ]
        self.assertEqual(1, len(reports))

    @async_test
    async def test_make_plots(self):
        await self.db.start(SAMPLE_DATASET)

        # Just run generation logic to ensure no runtime issues
        self.filter_full.outliers = 0.01
        path = await self.generator.make_plots(
            os.path.dirname(__file__), self.filter_full
        )
        self.assertTrue(os.path.exists(path))
        os.remove(path)

    def assertEqualDF(self, first: DataFrame, second: DataFrame):
        self.assertEqual(
            list(first.index.values), list(second.index.values), "Bad indexes"
        )
        self.assertEqual(
            list(first.columns.values), list(second.columns.values), "Bad columns"
        )
        if first.equals(second):
            return
        print("Expected:\n", first)
        print("Received:\n", second)
        self.fail("Bad data")
