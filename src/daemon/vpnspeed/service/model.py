from vpnspeed.model import *
from dataclasses import dataclass
from typing import List, Set, Dict
from copy import deepcopy


class State(Enum):
    quit = 0
    idle = 1
    run = 2

    def __getstate__(self):
        return self.name


@dataclass
class Case:
    case: TestCase
    run_count: int = 0
    fail_count: int = 0


@dataclass
class Group:
    group: TestGroup
    cases: List[Case]
    failing: bool = False


@dataclass
class Context:
    state: State = None
    probe: Probe = None
    config: Config = None
    groups: List[Group] = None
