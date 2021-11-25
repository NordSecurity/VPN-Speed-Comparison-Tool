import random
from .model import *


def _all_equal(iterator):
    iterator = iter(iterator)
    try:
        first = next(iterator)
    except StopIteration:
        return True
    return all(first == rest for rest in iterator)


def _select_least_runned_in_group(groups: List[Group]) -> (TestGroup, TestCase):
    groups_runs = [
        (group, min(case.run_count for case in group.cases))
        for group in groups
        if not group.failing
    ]
    if len(groups_runs) == 0:
        return None

    uneven = [
        (group, runs)
        for group, runs in groups_runs
        if not _all_equal(case.run_count for case in group.cases)
    ]
    if len(uneven) > 0:
        groups_runs = uneven

    min_runs = min(runs for _, runs in groups_runs)

    options = [
        (group.group, case.case)
        for group, runs in groups_runs
        for case in group.cases
        if case.run_count == min_runs and case.fail_count >= 0
    ]
    if len(options) == 0:
        return None
    return random.choice(options)


def select(groups: List[Group], *, method: str = None) -> (TestGroup, TestCase):
    return _select_least_runned_in_group(groups)
