from __future__ import annotations

import copy
from typing import Any

from app.plugins import SchemaOptionsProviderContext


async def resolve_plan_combox(
    *,
    options_provider: dict[str, Any],
    field_schema: dict[str, Any],
    config_data: dict[str, Any],
    ctx: SchemaOptionsProviderContext,
) -> list[dict[str, Any]]:
    _ = options_provider, field_schema, config_data

    data = [{"label": "固定", "value": "Fixed"}]
    plan_config = ctx.related_config.get("PlanConfig")
    if plan_config is None:
        return data

    for uid, plan in plan_config.items():
        data.append({"label": plan.get("Info", "Name"), "value": str(uid)})
    return data


async def resolve_stage_info(
    *,
    options_provider: dict[str, Any],
    field_schema: dict[str, Any],
    config_data: dict[str, Any],
    ctx: SchemaOptionsProviderContext,
) -> list[dict[str, Any]]:
    _ = field_schema, config_data, ctx

    from app.core import Config as RuntimeConfig

    stage_type = str(options_provider.get("type") or "User")
    raw_data = await RuntimeConfig.get_stage_info(stage_type)
    if not isinstance(raw_data, list):
        return []

    data = copy.deepcopy(raw_data)
    none_label = options_provider.get("none_label")
    if isinstance(none_label, str) and none_label.strip():
        for option in data:
            if isinstance(option, dict) and option.get("value") == "-":
                option["label"] = none_label
    return data
