def _group_string_to_dict(mapping: str):
    return {
        "vpn_country": mapping[: mapping.index(":")],
        "target_country": mapping[mapping.index(":") + 1 :],
    }


def _parse_groups_list(field_values: list):
    groups = []
    for item in field_values:
        if isinstance(item, dict):
            return field_values
        groups.append(_group_string_to_dict(item))
    return groups


def _parse_groups(field_values):
    groups = []
    if isinstance(field_values, list):
        groups = _parse_groups_list(field_values)
    elif isinstance(field_values, dict) and "multi" in field_values:
        for src in field_values["multi"].get("vpns", []):
            for dest in field_values["multi"].get("targets", []):
                groups.append(_group_string_to_dict(src + ":" + dest))
    return groups


def preparse(context: dict):
    if "config" not in context:
        return

    if "groups" in context["config"]:
        if not isinstance(context["config"]["groups"], list):
            context["config"]["groups"] = _parse_groups(context["config"]["groups"])
        elif isinstance(context["config"]["groups"], list):
            context["config"]["groups"] = _parse_groups_list(
                context["config"]["groups"]
            )

    if "sinks" not in context["config"]:
        context["config"]["sinks"] = []
