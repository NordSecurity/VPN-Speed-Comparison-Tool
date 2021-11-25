from vpnspeed.service.model import Context
from enum import Enum
from datetime import datetime, date


def _filter_none(d):
    if isinstance(d, dict):
        return {k: _filter_none(v) for k, v in d.items() if v is not None}
    elif isinstance(d, list):
        return [_filter_none(v) for v in d]
    else:
        return d


def _to_dict(obj):
    if isinstance(obj, dict):
        data = {}
        for (k, v) in obj.items():
            data[k] = _to_dict(v)
        return data
    elif isinstance(obj, (date, datetime)):
        return obj.isoformat()
    elif isinstance(obj, Enum):
        return obj.name
    elif hasattr(obj, "_ast"):
        return _to_dict(obj._ast())
    elif hasattr(obj, "__iter__") and not isinstance(obj, str):
        return [_to_dict(v) for v in obj]
    elif hasattr(obj, "__dict__"):
        data = dict(
            [
                (key, _to_dict(value))
                for key, value in obj.__dict__.items()
                if not callable(value) and not key.startswith("_")
            ]
        )
        return data
    else:
        return obj


def encode(context: Context) -> dict:
    return _filter_none(_to_dict(context))
