import unittest

import vpnspeed.service.model as m
from vpnspeed.service.select import select

OPTION = [
    (
        m.TestGroup(vpn_country=f"from-{i}", target_country=f"to-{i}"),
        m.TestCase(vpn=f"via-{i}"),
    )
    for i in range(4)
]


class TestSelect(unittest.TestCase):
    def test_select_least_run_case_in_group(self):
        groups = [
            m.Group(
                group=OPTION[0][0],
                cases=[
                    m.Case(
                        case=OPTION[0][1],
                        run_count=1,
                        fail_count=0,
                    ),
                    m.Case(
                        case=OPTION[1][1],
                        run_count=2,
                        fail_count=0,
                    ),
                    m.Case(
                        case=OPTION[2][1],
                        run_count=3,
                        fail_count=0,
                    ),
                ],
            )
        ]

        self.assertEqual(OPTION[0], select(groups))

    def test_select_least_run_case_in_groups(self):
        groups = [
            m.Group(
                group=OPTION[0][0],
                cases=[
                    m.Case(
                        case=OPTION[0][1],
                        run_count=1,
                        fail_count=0,
                    ),
                    m.Case(
                        case=OPTION[1][1],
                        run_count=2,
                        fail_count=0,
                    ),
                    m.Case(
                        case=OPTION[2][1],
                        run_count=2,
                        fail_count=0,
                    ),
                ],
            ),
            m.Group(
                group=OPTION[1][0],
                cases=[
                    m.Case(
                        case=OPTION[0][1],
                        run_count=2,
                        fail_count=0,
                    ),
                    m.Case(
                        case=OPTION[1][1],
                        run_count=2,
                        fail_count=0,
                    ),
                    m.Case(
                        case=OPTION[2][1],
                        run_count=2,
                        fail_count=0,
                    ),
                ],
            ),
            m.Group(
                group=OPTION[2][0],
                cases=[
                    m.Case(
                        case=OPTION[0][1],
                        run_count=5,
                        fail_count=0,
                    ),
                    m.Case(
                        case=OPTION[1][1],
                        run_count=4,
                        fail_count=0,
                    ),
                    m.Case(
                        case=OPTION[2][1],
                        run_count=3,
                        fail_count=0,
                    ),
                ],
            ),
            m.Group(
                group=OPTION[3][0],
                cases=[
                    m.Case(
                        case=OPTION[0][1],
                        run_count=100,
                        fail_count=0,
                    ),
                    m.Case(
                        case=OPTION[1][1],
                        run_count=2,
                        fail_count=0,
                    ),
                    m.Case(
                        case=OPTION[2][1],
                        run_count=2,
                        fail_count=0,
                    ),
                ],
            ),
        ]

        self.assertEqual(OPTION[0], select(groups))

    def test_select_case_from_lest_run_uneven_group(self):
        groups = [
            m.Group(
                group=OPTION[0][0],
                cases=[
                    m.Case(
                        case=OPTION[0][1],
                        run_count=4,
                        fail_count=0,
                    ),
                    m.Case(
                        case=OPTION[1][1],
                        run_count=5,
                        fail_count=0,
                    ),
                    m.Case(
                        case=OPTION[2][1],
                        run_count=5,
                        fail_count=0,
                    ),
                ],
            ),
            # Smaller and even
            m.Group(
                group=OPTION[1][0],
                cases=[
                    m.Case(
                        case=OPTION[0][1],
                        run_count=1,
                        fail_count=0,
                    ),
                    m.Case(
                        case=OPTION[1][1],
                        run_count=1,
                        fail_count=0,
                    ),
                    m.Case(
                        case=OPTION[2][1],
                        run_count=1,
                        fail_count=0,
                    ),
                ],
            ),
            # Bigger and even
            m.Group(
                group=OPTION[2][0],
                cases=[
                    m.Case(
                        case=OPTION[0][1],
                        run_count=5,
                        fail_count=0,
                    ),
                    m.Case(
                        case=OPTION[1][1],
                        run_count=5,
                        fail_count=0,
                    ),
                    m.Case(
                        case=OPTION[2][1],
                        run_count=5,
                        fail_count=0,
                    ),
                ],
            ),
            # Bigger and uneven
            m.Group(
                group=OPTION[3][0],
                cases=[
                    m.Case(
                        case=OPTION[0][1],
                        run_count=100,
                        fail_count=0,
                    ),
                    m.Case(
                        case=OPTION[1][1],
                        run_count=100,
                        fail_count=0,
                    ),
                    m.Case(
                        case=OPTION[2][1],
                        run_count=90,
                        fail_count=0,
                    ),
                ],
            ),
        ]

        self.assertEqual(OPTION[0], select(groups))

    def test_select_ignore_failing_case(self):
        groups = [
            m.Group(
                group=OPTION[0][0],
                cases=[
                    m.Case(
                        case=OPTION[0][1],
                        run_count=0,
                        fail_count=-1,
                    ),
                ],
            ),
        ]

        self.assertIsNone(select(groups))

    def test_select_ignore_failing_group(self):
        groups = [
            m.Group(
                group=OPTION[0][0],
                cases=[
                    m.Case(
                        case=OPTION[0][1],
                        run_count=2,
                        fail_count=0,
                    ),
                ],
                failing=True,
            ),
        ]

        self.assertIsNone(select(groups))
