from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.plugins.fields import PluginField

from .constants import MAA_STAGE_KEY, MAA_TASK_OPTIONS, RESOURCE_STAGE_INFO, UTC4, UTC8


def _option_values(values: list[str]) -> list[dict[str, str]]:
    return [{"label": value, "value": value} for value in values]


_MAA_TASK_ORDER = [str(item["value"]) for item in MAA_TASK_OPTIONS]
_MAA_TASK_FLAG_ORDER = [
    ("IfStartUp", "StartUp"),
    ("IfFight", "Fight"),
    ("IfInfrast", "Infrast"),
    ("IfRecruit", "Recruit"),
    ("IfMall", "Mall"),
    ("IfAward", "Award"),
    ("IfRoguelike", "Roguelike"),
    ("IfReclamation", "Reclamation"),
]


def _normalize_enabled_tasks(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []

    selected = {str(item) for item in value}
    normalized: list[str] = []
    for task in _MAA_TASK_ORDER:
        if task in selected:
            normalized.append(task)
    return normalized


def _enabled_tasks_from_legacy_flags(data: dict[str, Any]) -> list[str]:
    normalized: list[str] = []
    for legacy_key, task in _MAA_TASK_FLAG_ORDER:
        if data.get(legacy_key) is True:
            normalized.append(task)
    return normalized


def _is_task_enabled(config: Any, task: str) -> bool:
    tasks = _normalize_enabled_tasks(config.get("Task", "EnabledTasks"))
    return task in tasks


def _get_stage_zh(stage: str) -> str:
    for stage_info in RESOURCE_STAGE_INFO:
        if stage_info.get("value") == stage:
            return (
                stage_info.get("text", stage)
                .replace("经验-6/5", "经验")
                .replace("龙门币-6/5", "龙门币")
                .replace("红票-5", "红票")
                .replace("技能-5", "技能")
                .replace("碳-5", "碳")
            )
    return stage


def _build_infrast_name(config: Any) -> str:
    if config.get("Info", "InfrastMode") != "Custom":
        return "未使用自定义基建模式"

    infrast_data = json.loads(config.get("Data", "CustomInfrast"))
    if (
        infrast_data.get("title", "文件标题") != "文件标题"
        and infrast_data.get("description", "文件描述") != "文件描述"
    ):
        return f"{infrast_data['title']} - {infrast_data['description']}"
    if infrast_data.get("title", "文件标题") != "文件标题":
        return str(infrast_data["title"])
    if infrast_data.get("id") is not None:
        return str(infrast_data["id"])
    return "未命名自定义基建"


def _build_infrast_index(config: Any) -> str:
    if config.get("Info", "InfrastMode") != "Custom":
        return "-1"

    infrast_data = json.loads(config.get("Data", "CustomInfrast"))
    if len(infrast_data.get("plans", [])) == 0:
        return "-1"

    for index, plan in enumerate(infrast_data.get("plans", [])):
        for period in plan.get("period", []):
            if (
                datetime.strptime(period[0], "%H:%M").time()
                <= datetime.now().time()
                <= datetime.strptime(period[1], "%H:%M").time()
            ):
                return str(index)

    return config.get("Data", "InfrastIndex") or "0"


def _build_user_tags(config: Any) -> str:
    """生成 MAA 用户标签列表。"""

    tags: list[dict[str, str]] = []

    if not config.get("Data", "IfPassCheck"):
        tags.append({"text": "人工排查未通过", "color": "red"})

    if (
        datetime.strptime(config.get("Data", "LastProxyDate"), "%Y-%m-%d").date()
        == datetime.now(tz=UTC4).date()
    ):
        tags.append(
            {
                "text": f"日常：已代理{config.get('Data', 'ProxyTimes')}次",
                "color": "green",
            }
        )
    else:
        tags.append({"text": "日常：未代理", "color": "orange"})

    if config.get("Stage", "IfSkland"):
        if (
            datetime.strptime(config.get("Data", "LastSklandDate"), "%Y-%m-%d").date()
            == datetime.now(tz=UTC8).date()
        ):
            tags.append({"text": "森空岛：已签到", "color": "green"})
        else:
            tags.append({"text": "森空岛：未签到", "color": "orange"})
    else:
        tags.append({"text": "森空岛：禁用", "color": "red"})

    remained_day = config.get("Info", "RemainedDay")
    if remained_day == -1:
        tag_color = "gold"
    elif remained_day == 0:
        tag_color = "red"
    elif remained_day <= 3:
        tag_color = "orange"
    elif remained_day <= 7:
        tag_color = "yellow"
    elif remained_day <= 30:
        tag_color = "blue"
    else:
        tag_color = "green"
    tags.append(
        {
            "text": (
                f"剩余天数：{remained_day}天"
                if remained_day >= 0
                else "剩余天数：无期限"
            ),
            "color": tag_color,
        }
    )

    infrast_mode = config.get("Info", "InfrastMode")
    if _is_task_enabled(config, "Infrast"):
        if infrast_mode == "Normal":
            infrast_text = "基建：常规"
        elif infrast_mode == "Rotation":
            infrast_text = "基建：轮换"
        elif infrast_mode == "Custom":
            infrast_name = _build_infrast_name(config)
            infrast_text = (
                f"基建：{infrast_name}"
                if len(infrast_name) < 10
                else f"基建：{infrast_name[:10]}..."
            )
        else:
            infrast_text = "基建：开启"
        tags.append({"text": infrast_text, "color": "purple"})
    else:
        tags.append({"text": "基建：关闭", "color": "red"})

    plan_data = {
        stage_key: _get_stage_zh(config.get("Stage", stage_key))
        for stage_key in MAA_STAGE_KEY[2:]
    }
    tag_color = "blue"
    if config.get("Info", "StageMode") != "Fixed":
        try:
            plan = config.related_config["PlanConfig"][
                uuid.UUID(config.get("Info", "StageMode"))
            ]
        except Exception:
            plan = None
        if hasattr(plan, "get_current_info"):
            plan_data = {
                stage_key: _get_stage_zh(plan.get_current_info(stage_key).getValue())
                for stage_key in MAA_STAGE_KEY[2:]
            }
            tag_color = "green"

    tags.append({"text": f"主关卡：{plan_data['Stage']}", "color": tag_color})

    backup_stages = [
        plan_data[f"Stage_{index}"]
        for index in range(1, 4)
        if plan_data[f"Stage_{index}"] != "禁用"
    ]
    if backup_stages:
        tags.append({"text": f"备选：{', '.join(backup_stages)}", "color": tag_color})
    if plan_data["Stage_Remain"] != "禁用":
        tags.append({"text": f"剩余：{plan_data['Stage_Remain']}", "color": tag_color})

    notes = config.get("Info", "Notes")
    tags.append(
        {
            "text": f"备注：{notes}" if len(notes) <= 20 else f"备注：{notes[:20]}...",
            "color": "pink",
        }
    )

    return json.dumps(tags, ensure_ascii=False)


class Config(BaseModel):
    """插件实例配置。"""

    model_config = ConfigDict(extra="allow")

    plain_text: str = PluginField(
        default="请直接在脚本配置使用本插件",
        title="专项适配",
        description="请直接在脚本配置使用本插件",
        min_length=2,
        max_length=32,
        size="1/3"
    )


class MaaScriptInfo(BaseModel):
    Name: str = PluginField("新 MAA 脚本", title="脚本名称")
    Path: str = PluginField(
        str(Path.home()),
        title="MAA 根目录",
        ui_type="folder",
        path_kind="folder",
        placeholder="请选择 MAA 的安装目录",
        size="2/3",
    )


class MaaScriptEmulator(BaseModel):
    Id: str = PluginField(
        "-",
        title="模拟器",
        ui_type="related-id",
        related_config="EmulatorConfig",
    )
    Index: str = PluginField(
        "-",
        title="多开实例",
        help="选择多开序号；若列表为空，可保持为“未选择”后由运行时自动处理。",
    )


class MaaScriptRun(BaseModel):
    TaskTransitionMethod: Literal["NoAction", "ExitGame", "ExitEmulator"] = PluginField(
        "ExitEmulator",
        title="任务切换方式",
        options=_option_values(["NoAction", "ExitGame", "ExitEmulator"]),
    )
    ProxyTimesLimit: int = PluginField(0, title="代理次数限制", ge=0, le=9999, step=1)
    RunTimesLimit: int = PluginField(3, title="运行次数限制", ge=1, le=9999, step=1)
    AnnihilationTimeLimit: int = PluginField(
        40,
        title="剿灭时间限制（分钟）",
        ge=1,
        le=9999,
        step=1,
    )
    RoutineTimeLimit: int = PluginField(
        10,
        title="日常时间限制（分钟）",
        ge=1,
        le=9999,
        step=1,
    )
    AnnihilationAvoidWaste: bool = PluginField(False, title="剿灭避免浪费理智")


class MaaScriptNotify(BaseModel):
    Channels: list[str] = PluginField(
        default_factory=list,
        title="通知频道",
        ui_type="multiselect",
        options_provider={"source": "notification_channels"},
        help="为空时不使用通知；选择 all 时发送给 notify 插件当前已注册的全部频道；选择其他频道时仅发送给指定频道。",
        size="large",
    )


class MaaScriptAction(BaseModel):
    MAAConfig: str = PluginField(
        "",
        title="MAA配置",
        ui_type="readonly",
        readonly=True,
        json_schema_extra={"icon": "SettingOutlined"},
        help="启动 MAA 默认配置会话，完成后点击保存配置结束会话。",
        button={
            "label": "MAA配置",
            "path": "/api/dispatch/start",
            "method": "POST",
            "payload": {"taskId": "{{scriptId}}", "mode": "ScriptConfig"},
            "refresh": True,
            "session": {
                "response_task_id_key": "taskId",
                "stop_path": "/api/dispatch/stop",
                "stop_method": "POST",
                "stop_payload": {"taskId": "{{session.websocketId}}"},
                "overlay_title": "正在进行 MAA 默认配置",
                "overlay_description": (
                    "当前正在启动 MAA 默认配置，请在 MAA 窗口中完成配置。\n"
                    "配置完成后，请点击“保存配置”以写回默认配置。"
                ),
                "stop_label": "保存配置",
                "start_message": "已开始 {{scriptName}} 的 MAA 默认配置",
                "success_message": "{{scriptName}} 的 MAA 默认配置已完成",
                "stop_message": "{{scriptName}} 的 MAA 默认配置已保存",
                "timeout_ms": 1800000,
                "timeout_auto_stop": True,
                "timeout_message": (
                    "{{scriptName}} 的 MAA 默认配置会话已超时（30分钟），正在自动保存配置..."
                ),
            },
        },
    )


class MaaConfigModel(BaseModel):
    Info: MaaScriptInfo = Field(default_factory=MaaScriptInfo, title="基础信息")
    Emulator: MaaScriptEmulator = Field(default_factory=MaaScriptEmulator, title="模拟器设置")
    Run: MaaScriptRun = Field(default_factory=MaaScriptRun, title="运行设置")
    Notify: MaaScriptNotify = Field(default_factory=MaaScriptNotify, title="通知设置")
    Action: MaaScriptAction = Field(default_factory=MaaScriptAction, title="交互操作")


class MaaUserInfo(BaseModel):
    Name: str = PluginField("新用户", title="用户名称", validator="username")
    Id: str = PluginField("", title="用户 ID")
    Password: str = PluginField(
        "",
        title="密码",
        format="password",
        json_schema_extra={"sensitive": True},
    )
    Mode: Literal["简洁", "详细"] = PluginField("简洁", title="展示模式")
    StageMode: str = PluginField(
        "Fixed",
        title="关卡模式",
        ui_type="related-id",
        related_config="PlanConfig",
        options_provider={"source": "plan_combox"},
    )
    Server: Literal["Official", "Bilibili", "YoStarEN", "YoStarJP", "YoStarKR", "txwy"] = (
        PluginField(
            "Official",
            title="服务器",
            options=_option_values(
                ["Official", "Bilibili", "YoStarEN", "YoStarJP", "YoStarKR", "txwy"]
            ),
        )
    )
    Status: bool = PluginField(True, title="启用用户")
    RemainedDay: int = PluginField(-1, title="剩余天数", ge=-1, le=9999, step=1)
    Annihilation: Literal[
        "Close",
        "Annihilation",
        "Chernobog@Annihilation",
        "LungmenOutskirts@Annihilation",
        "LungmenDowntown@Annihilation",
    ] = PluginField(
        "Annihilation",
        title="剿灭设置",
        options=[
            {"label": "不使用剿灭", "value": "Close"},
            {"label": "剿灭", "value": "Annihilation"},
            {"label": "龙门市区", "value": "LungmenDowntown@Annihilation"},
            {"label": "龙门外环", "value": "LungmenOutskirts@Annihilation"},
            {"label": "切尔诺伯格", "value": "Chernobog@Annihilation"},
        ],
    )
    InfrastMode: Literal["Normal", "Rotation", "Custom"] = PluginField(
        "Normal",
        title="基建模式",
        options=[
            {"label": "常规模式", "value": "Normal"},
            {"label": "一键轮休", "value": "Rotation"},
            {"label": "自定义基建", "value": "Custom"},
        ],
    )
    InfrastName: str = PluginField(
        "",
        title="自定义基建名称",
        ui_type="readonly",
        readonly=True,
        json_schema_extra={"virtual_handler": _build_infrast_name},
    )
    InfrastIndex: str = PluginField(
        "-",
        title="当前班次索引",
        ui_type="readonly",
        readonly=True,
        json_schema_extra={"virtual_handler": _build_infrast_index},
    )
    Notes: str = PluginField(
        "无",
        title="备注",
        rows=4,
        size="large",
        placeholder="填写该用户的备注信息",
    )
    Tag: str = PluginField(
        "[ ]",
        title="用户标签",
        ui_type="tag",
        readonly=True,
        hidden=True,
        help="运行时自动生成，仅用于展示。",
        json_schema_extra={"virtual_handler": _build_user_tags},
    )


class MaaUserStage(BaseModel):
    MedicineNumb: int = PluginField(0, title="吃理智药数量", ge=0, le=9999, step=1,size="1/2")
    SeriesNumb: Literal["0", "6", "5", "4", "3", "2", "1", "-1"] = PluginField(
        "0",
        title="连战次数",
        options=[
            {"label": "AUTO", "value": "0"},
            {"label": "1", "value": "1"},
            {"label": "2", "value": "2"},
            {"label": "3", "value": "3"},
            {"label": "4", "value": "4"},
            {"label": "5", "value": "5"},
            {"label": "6", "value": "6"},
            {"label": "不切换", "value": "-1"},
        ],
        size="1/2"
    )
    Stage: str = PluginField(
        "-",
        title="主关卡",
        size="large",
        placeholder="选择或输入自定义关卡",
        options_provider={"source": "stage_info", "type": "Today", "allow_custom": True},
    )
    Stage_1: str = PluginField(
        "-",
        title="备选关卡 1",
        size="1/4",
        placeholder="选择或输入自定义关卡",
        options_provider={"source": "stage_info", "type": "Today", "allow_custom": True},
    )
    Stage_2: str = PluginField(
        "-",
        title="备选关卡 2",
        size="1/4",
        placeholder="选择或输入自定义关卡",
        options_provider={"source": "stage_info", "type": "Today", "allow_custom": True},
    )
    Stage_3: str = PluginField(
        "-",
        title="备选关卡 3",
        size="1/4",
        placeholder="选择或输入自定义关卡",
        options_provider={"source": "stage_info", "type": "Today", "allow_custom": True},
    )
    Stage_Remain: str = PluginField(
        "-",
        title="剩余理智关卡",
        size="1/4",
        placeholder="选择或输入自定义关卡",
        help="选择“不选择”时，将不使用剩余理智关卡。",
        options_provider={
            "source": "stage_info",
            "type": "Today",
            "allow_custom": True,
            "none_label": "不选择",
        },
    )
    IfSkland: bool = PluginField(False, title="森空岛签到")
    SklandToken: str = PluginField(
        "",
        title="森空岛 Token",
        format="password",
        json_schema_extra={"sensitive": True},
        size="2/3"
    )


class MaaUserTask(BaseModel):
    EnabledTasks: list[str] = PluginField(
        default_factory=lambda: _MAA_TASK_ORDER[:6],
        title="任务开关",
        ui_type="multiselect",
        options=MAA_TASK_OPTIONS,
        size="1/2",
        json_schema_extra={"selection_mode": "ordered"},
    )

    @model_validator(mode="before")
    @classmethod
    def _upgrade_legacy_task_flags(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value

        data = dict(value)
        enabled_tasks = data.get("EnabledTasks")
        if enabled_tasks is None:
            data["EnabledTasks"] = _enabled_tasks_from_legacy_flags(data)
        else:
            data["EnabledTasks"] = _normalize_enabled_tasks(enabled_tasks)
        return data


class MaaUserNotify(BaseModel):
    Enabled: bool = PluginField(False, title="启用通知")
    IfSendStatistic: bool = PluginField(False, title="发送统计信息")
    IfSendSixStar: bool = PluginField(False, title="发送高资喜报")
    IfSendMail: bool = PluginField(False, title="邮件通知")
    ToAddress: str = PluginField("", title="收件邮箱")
    IfServerChan: bool = PluginField(False, title="Server酱通知")
    ServerChanKey: str = PluginField("", title="Server酱 SENDKEY")


class MaaUserData(BaseModel):
    LastProxyDate: str = PluginField(
        "2000-01-01",
        title="上次代理日期",
        ui_type="datetime",
        format="%Y-%m-%d",
        readonly=True,
        help="运行结束后自动更新。",
    )
    LastSklandDate: str = PluginField(
        "2000-01-01",
        title="上次森空岛签到日期",
        ui_type="datetime",
        format="%Y-%m-%d",
        readonly=True,
        help="运行结束后自动更新。",
    )
    ProxyTimes: int = PluginField(
        0,
        title="今日代理次数",
        ge=0,
        le=9999,
        step=1,
        readonly=True,
        help="运行结束后自动更新。",
    )
    IfPassCheck: bool = PluginField(True, title="人工排查通过")
    CustomInfrast: str = PluginField(
        "{ }",
        title="自定义基建 JSON",
        ui_type="json",
        json_type="object",
        rows=12,
        size="large",
    )
    ImportCustomInfrast: str = PluginField(
        "",
        title="导入自定义基建 JSON",
        ui_type="button",
        configurable=False,
        help="选择本地 JSON 文件后，会按现有基建导入接口同步到当前用户。",
        button={
            "label": "导入自定义基建 JSON",
            "path": "/api/scripts/user/infrastructure",
            "method": "POST",
            "payload": {
                "scriptId": "{{scriptId}}",
                "userId": "{{userId}}",
                "jsonFile": "{{pickedFile}}",
            },
            "refresh": True,
            "file_picker": {
                "filters": [{"name": "JSON Files", "extensions": ["json"]}],
            },
        },
    )
    InfrastIndex: str = PluginField(
        "0",
        title="自定义基建排班",
        json_schema_extra={"legacy_group": "Info"},
    )


class MaaUserConfigModel(BaseModel):
    Info: MaaUserInfo = Field(default_factory=MaaUserInfo, title="基础信息")
    Stage: MaaUserStage = Field(default_factory=MaaUserStage, title="关卡设置")
    Task: MaaUserTask = Field(default_factory=MaaUserTask, title="任务开关")
    Notify: MaaUserNotify = Field(default_factory=MaaUserNotify, title="通知设置")
    Data: MaaUserData = Field(default_factory=MaaUserData, title="运行数据")


__all__ = [
    "Config",
    "MaaConfigModel",
    "MaaUserConfigModel",
]
