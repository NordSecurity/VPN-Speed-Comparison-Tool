import dataclasses
from datetime import date, datetime
from enum import EnumMeta
from vpnspeed import log
from vpnspeed.utils import iso_to_cc
from vpnspeed.service.model import Context, Probe, TestGroup
from .preparser import preparse
from .validator import validate_format, validate_values


def _get_field_type(obj_type, field_name):
    for field in dataclasses.fields(obj_type):
        if field.name == field_name:
            return field.type
    return None


def _list_to_obj(item_list, item_type):
    items = []
    for item in item_list:
        items.append(_dict_to_obj(item, item_type))
    return items


def _dict_to_obj(field_values: dict, obj_type: type) -> object:
    obj = obj_type(**field_values)
    for field_name, value in obj.__dict__.items():
        field_type = _get_field_type(obj_type, field_name)

        if value is None:
            continue

        elif isinstance(value, dict):
            obj.__dict__[field_name] = (
                _dict_to_obj(value, field_type) if field_type != dict else value
            )

        elif isinstance(value, list):
            list_elem_type = field_type.__args__[0]
            if list_elem_type != int and list_elem_type != str:
                obj.__dict__[field_name] = _list_to_obj(value, list_elem_type)

        elif field_type == date:
            obj.__dict__[field_name] = date.fromisoformat(value)

        elif field_type == datetime:
            obj.__dict__[field_name] = datetime.fromisoformat(value)

        elif type(field_type) == EnumMeta:
            obj.__dict__[field_name] = field_type[value]

        elif field_type not in (str, int, float, bool) and value:
            obj.__dict__[field_name] = field_type(value)

    return obj


def format_countries(context: Context):
    if context is None:
        return

    if context.probe:
        context.probe = Probe(
            **{
                **context.probe.__dict__,
                "country_code": iso_to_cc(context.probe.country_code),
            }
        )

    if context.config and context.config.groups:
        context.config.groups = [
            TestGroup(
                **{
                    **group.__dict__,
                    "vpn_country": iso_to_cc(group.vpn_country),
                    "target_country": iso_to_cc(group.target_country),
                }
            )
            for group in context.config.groups
        ]


def decode(dict_: dict) -> Context:
    preparse(dict_)
    # validate_format(dict_)
    context = _dict_to_obj(dict_, Context)
    validate_values(context)
    format_countries(context)
    return context
