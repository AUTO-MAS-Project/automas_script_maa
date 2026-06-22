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
    # 构建固定模式与计划表选项。
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
    # 获取当前可用的关卡选项。
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


async def resolve_notification_channels(
    *,
    options_provider: dict[str, Any],
    field_schema: dict[str, Any],
    config_data: dict[str, Any],
    ctx: SchemaOptionsProviderContext,
) -> list[dict[str, Any]]:
    # 获取 notify 服务已注册的通知频道。
    _ = options_provider, field_schema, config_data, ctx

    data: list[dict[str, Any]] = [{"label": "全部通知频道", "value": "all"}]

    try:
        from app.plugins import PluginManager

        notify = PluginManager.service.get("notify")
    except Exception:
        notify = None

    channels = getattr(notify, "channels", None)
    if not callable(channels):
        return data

    try:
        raw_channels = channels(detail=True)
    except TypeError:
        raw_channels = channels()
    except Exception:
        return data

    for item in raw_channels:
        if isinstance(item, dict):
            name = str(item.get("name") or "").strip()
            if not name or name == "all":
                continue
            label = name
            enabled = item.get("enabled")
            channel_type = str(item.get("type") or "").strip()
            if channel_type:
                label = f"{name} ({channel_type})"
            if enabled is False:
                label = f"{label} - disabled"
            data.append({"label": label, "value": name})
        else:
            name = str(item or "").strip()
            if name and name != "all":
                data.append({"label": name, "value": name})
    return data
