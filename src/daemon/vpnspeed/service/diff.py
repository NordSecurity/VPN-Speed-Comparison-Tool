"""
Pure functions to calculate new Context and Actions to take

None in new always indicates no change
"""

from typing import List, Set, Dict

from .model import *

# Action Model


def iota(start):
    index = start - 1

    def next():
        nonlocal index
        index += 1
        return index

    return next


_action_iota = iota(-1)


@dataclass
class Action:
    mark = _action_iota()


@dataclass
class Quit(Action):
    mark = _action_iota()


@dataclass
class Stop(Action):
    mark = _action_iota()


@dataclass
class RemoveGroups(Action):
    mark = _action_iota()
    groups: Set[TestGroup]


@dataclass
class RemoveCases(Action):
    mark = _action_iota()
    cases: Set[TestCase]


@dataclass
class AddCases(Action):
    mark = _action_iota()
    cases: Set[TestCase]


@dataclass
class AddGroups(Action):
    mark = _action_iota()
    groups: Set[TestGroup]


@dataclass
class RemoveDataSinks(Action):
    mark = _action_iota()
    sinks: List[DataSink]


@dataclass
class UpdateDataSinks(Action):
    mark = _action_iota()
    sinks: List[DataSink]


@dataclass
class AddDataSinks(Action):
    mark = _action_iota()
    sinks: List[DataSink]


@dataclass
class RemoveVPNs(Action):
    mark = _action_iota()
    vpns: List[VPN]


@dataclass
class UpdateVPNs(Action):
    mark = _action_iota()
    vpns: List[VPN]


@dataclass
class AddVPNs(Action):
    mark = _action_iota()
    vpns: List[VPN]


@dataclass
class Start(Action):
    mark = _action_iota()


del _action_iota


def diff_vpns(old: List[VPN], new: List[VPN]) -> (List[VPN], List[Action]):
    actions = []
    if new is None:
        return (deepcopy(old), actions)

    # Compare existing vpn with new, update/set new, unset old
    old_vpns = {vpn.name: vpn for vpn in old}
    new_vpns = {vpn.name: vpn for vpn in new}

    del_vpns = []
    update_vpns = []
    for name in old_vpns.keys():
        if name in new_vpns:
            if old_vpns[name] != new_vpns[name]:
                update_vpns.append(new_vpns[name])
            del new_vpns[name]
        else:
            del_vpns.append(old_vpns[name])
    add_vpns = new_vpns.values()

    if add_vpns:
        actions.append(AddVPNs(vpns=add_vpns))
    if update_vpns:
        actions.append(UpdateVPNs(vpns=update_vpns))
    if del_vpns:
        actions.append(RemoveVPNs(vpns=del_vpns))

    # Generate all new possible TestCase permutations [vpn x technology x protocol
    def to_cases(vpns: List[VPN]):
        cases = set()
        for vpn in vpns:
            for tech in vpn.technologies or []:
                for proto in tech.protocols or [None]:
                    cases.add(
                        TestCase(
                            vpn=vpn.name,
                            technology=tech.name,
                            protocol=proto,
                        )
                    )
        return cases

    old_cases = to_cases(old)
    new_cases = to_cases(new)

    delc = old_cases - new_cases
    addc = new_cases - old_cases

    if delc:
        actions.append(RemoveCases(cases=delc))
    if addc:
        actions.append(AddCases(cases=addc))
    return (deepcopy(new), actions)


def diff_groups(
    old: Set[TestGroup], new: Set[TestGroup]
) -> (Set[TestGroup], List[Action]):
    actions = []
    if new is None:
        return (deepcopy(old), actions)

    delg = old - new
    addg = new - old

    if delg:
        actions.append(RemoveGroups(groups=delg))
    if addg:
        actions.append(AddGroups(groups=addg))

    return (deepcopy(new), actions)


def diff_sinks(
    old: List[DataSink], new: List[DataSink]
) -> (List[DataSink], List[Action]):
    actions = []
    if new is None:
        return (deepcopy(old), actions)

    old_dict = {sink.name: sink for sink in old}
    a, u, d = [], [], []
    for sink in new:
        if sink.name in old_dict:
            if sink != old_dict[sink.name]:
                u.append(sink)
            del old_dict[sink.name]
        else:
            a.append(sink)
    d.extend(old_dict.values())

    if a:
        actions.append(AddDataSinks(sinks=a))
    if u:
        actions.append(UpdateDataSinks(sinks=u))
    if d:
        actions.append(RemoveDataSinks(sinks=d))

    return (deepcopy(new), actions)


def diff_config(old: Config, new: Config) -> (Config, List[Action]):
    actions = []

    if new is None:
        return (deepcopy(old), actions)

    vpns, act = diff_vpns(old and old.vpns or [], new.vpns)
    actions.extend(act)

    groups, act = diff_groups(old and old.groups or set(), set(new.groups or []))
    actions.extend(act)

    sinks, act = diff_sinks(old and old.sinks or [], new.sinks)
    actions.extend(act)

    config = Config(
        interval=new.interval or old.interval,
        mode=new.mode or old.mode,
        repeats=new.repeats or old.repeats,
        common_cities=new.common_cities or old.common_cities,
        vpns=vpns,
        groups=groups,
        sinks=sinks,
    )
    if new.mode is not None and old.mode != new.mode:
        # Retstart runner on mode change
        actions.extend(
            [
                Stop(),
                Start(),
            ]
        )

    return (config, actions)


def diff_context(old: Context, new: Context) -> (Context, List[Action]):
    if new is None:
        return (deepcopy(old), [])

    config, actions = diff_config(old.config, new.config)

    context = Context(
        state=new.state or old.state,
        probe=new.probe or old.probe,
        config=config,
    )

    # State change diff
    if old.state == State.idle and context.state == State.run:
        actions.append(Start())
    elif old.state == State.run and context.state == State.idle:
        actions.append(Stop())
    elif context.state == State.quit:
        actions.append(Quit())

    return (context, actions)
