from jsonpath_ng import parse
from jsonpath_ng.jsonpath import *


def _update(data: dict, path: JSONPath, value):
    if isinstance(path, Child):
        lrefs = _update(data, path.left, [] if isinstance(path.right, Index) else {})
        return [rref for lref in lrefs for rref in _update(lref, path.right, value)]
    if isinstance(path, (Root, This)):
        data.update(value)
        return [data]
    if isinstance(path, Fields):
        refs = []
        for field in path.fields:
            if field in data:
                if isinstance(data[field], dict):
                    data[field].update(value)
                elif isinstance(data[field], list):
                    data[field].extend(value)
                else:
                    data[field] = value
            else:
                data[field] = value
            refs.append(data[field])
        return refs
    if isinstance(path, Index):
        if isinstance(data, list):
            data.append(value)
            return [value]
        if isinstance(data, dict):
            data[path.index] = value
            return [value]
        return []

    return []


def filter(data: dict, path: str) -> dict:
    jsonpath = parse(path)
    result = {}

    for match in jsonpath.find(data):
        _update(result, match.full_path, match.value)

    return result
