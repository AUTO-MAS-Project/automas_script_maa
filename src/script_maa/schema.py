from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path

from app.core.plugins.fields import PluginField
from pydantic import BaseModel, ConfigDict

from app.models.ConfigBase import (
    BoolValidator,
    ConfigBase,
    ConfigItem,
    DateTimeValidator,
    EncryptValidator,
    FolderValidator,
    JSONValidator,
    MultipleConfig,
    MultipleUIDValidator,
    OptionsValidator,
    RangeValidator,
    URLValidator,
    UserNameValidator,
    VirtualConfigValidator,
)
from app.utils.constants import MAA_STAGE_KEY, RESOURCE_STAGE_INFO, UTC4, UTC8


class Config(BaseModel):
    """插件实例配置。"""

    model_config = ConfigDict(extra="allow")

    reserved: str = PluginField(default="", description="预留字段，当前无需配置")


class Webhook(ConfigBase):
    """Webhook 配置。"""

    def __init__(self) -> None:
        self.Info_Name = ConfigItem("Info", "Name", "新自定义 Webhook 通知")
        self.Info_Enabled = ConfigItem("Info", "Enabled", True, BoolValidator())

        self.Data_Url = ConfigItem("Data", "Url", "", URLValidator())
        self.Data_Template = ConfigItem("Data", "Template", "")
        self.Data_Headers = ConfigItem("Data", "Headers", "{ }", JSONValidator())
        self.Data_Method = ConfigItem(
            "Data", "Method", "POST", OptionsValidator(["POST", "GET"])
        )

        super().__init__()


class MaaUserConfig(ConfigBase):
    """MAA 用户配置。"""

    related_config: dict[str, MultipleConfig] = {}

    def __init__(self) -> None:
        self.Info_Name = ConfigItem("Info", "Name", "新用户", UserNameValidator())
        self.Info_Id = ConfigItem("Info", "Id", "")
        self.Info_Password = ConfigItem("Info", "Password", "", EncryptValidator())
        self.Info_Mode = ConfigItem(
            "Info", "Mode", "简洁", OptionsValidator(["简洁", "详细"])
        )
        self.Info_StageMode = ConfigItem(
            "Info",
            "StageMode",
            "Fixed",
            MultipleUIDValidator("Fixed", self.related_config, "PlanConfig"),
        )
        self.Info_Server = ConfigItem(
            "Info",
            "Server",
            "Official",
            OptionsValidator(
                ["Official", "Bilibili", "YoStarEN", "YoStarJP", "YoStarKR", "txwy"]
            ),
        )
        self.Info_Status = ConfigItem("Info", "Status", True, BoolValidator())
        self.Info_RemainedDay = ConfigItem(
            "Info", "RemainedDay", -1, RangeValidator(-1, 9999)
        )
        self.Info_Annihilation = ConfigItem(
            "Info",
            "Annihilation",
            "Annihilation",
            OptionsValidator(
                [
                    "Close",
                    "Annihilation",
                    "Chernobog@Annihilation",
                    "LungmenOutskirts@Annihilation",
                    "LungmenDowntown@Annihilation",
                ]
            ),
        )
        self.Info_InfrastMode = ConfigItem(
            "Info",
            "InfrastMode",
            "Normal",
            OptionsValidator(["Normal", "Rotation", "Custom"]),
        )
        self.Info_InfrastName = ConfigItem(
            "Info", "InfrastName", "-", VirtualConfigValidator(self.getInfrastName)
        )
        self.Info_InfrastIndex = ConfigItem(
            "Info", "InfrastIndex", "-", VirtualConfigValidator(self.getInfrastIndex)
        )
        self.Info_Notes = ConfigItem("Info", "Notes", "无")
        self.Info_MedicineNumb = ConfigItem(
            "Info", "MedicineNumb", 0, RangeValidator(0, 9999)
        )
        self.Info_SeriesNumb = ConfigItem(
            "Info",
            "SeriesNumb",
            "0",
            OptionsValidator(["0", "6", "5", "4", "3", "2", "1", "-1"]),
        )
        self.Info_Stage = ConfigItem("Info", "Stage", "-")
        self.Info_Stage_1 = ConfigItem("Info", "Stage_1", "-")
        self.Info_Stage_2 = ConfigItem("Info", "Stage_2", "-")
        self.Info_Stage_3 = ConfigItem("Info", "Stage_3", "-")
        self.Info_Stage_Remain = ConfigItem("Info", "Stage_Remain", "-")
        self.Info_IfSkland = ConfigItem("Info", "IfSkland", False, BoolValidator())
        self.Info_SklandToken = ConfigItem("Info", "SklandToken", "", EncryptValidator())
        self.Info_Tag = ConfigItem(
            "Info", "Tag", "[ ]", VirtualConfigValidator(self.getTags)
        )

        self.Data_LastProxyDate = ConfigItem(
            "Data", "LastProxyDate", "2000-01-01", DateTimeValidator("%Y-%m-%d")
        )
        self.Data_LastSklandDate = ConfigItem(
            "Data", "LastSklandDate", "2000-01-01", DateTimeValidator("%Y-%m-%d")
        )
        self.Data_ProxyTimes = ConfigItem(
            "Data", "ProxyTimes", 0, RangeValidator(0, 9999)
        )
        self.Data_IfPassCheck = ConfigItem("Data", "IfPassCheck", True, BoolValidator())
        self.Data_CustomInfrast = ConfigItem(
            "Data", "CustomInfrast", "{ }", JSONValidator()
        )
        self.Data_InfrastIndex = ConfigItem(
            "Data", "InfrastIndex", "0", legacy_group="Info"
        )

        self.Task_IfStartUp = ConfigItem("Task", "IfStartUp", True, BoolValidator())
        self.Task_IfFight = ConfigItem("Task", "IfFight", True, BoolValidator())
        self.Task_IfInfrast = ConfigItem("Task", "IfInfrast", True, BoolValidator())
        self.Task_IfRecruit = ConfigItem("Task", "IfRecruit", True, BoolValidator())
        self.Task_IfMall = ConfigItem("Task", "IfMall", True, BoolValidator())
        self.Task_IfAward = ConfigItem("Task", "IfAward", True, BoolValidator())
        self.Task_IfRoguelike = ConfigItem(
            "Task", "IfRoguelike", False, BoolValidator()
        )
        self.Task_IfReclamation = ConfigItem(
            "Task", "IfReclamation", False, BoolValidator()
        )

        self.Notify_Enabled = ConfigItem("Notify", "Enabled", False, BoolValidator())
        self.Notify_IfSendStatistic = ConfigItem(
            "Notify", "IfSendStatistic", False, BoolValidator()
        )
        self.Notify_IfSendSixStar = ConfigItem(
            "Notify", "IfSendSixStar", False, BoolValidator()
        )
        self.Notify_IfSendMail = ConfigItem(
            "Notify", "IfSendMail", False, BoolValidator()
        )
        self.Notify_ToAddress = ConfigItem("Notify", "ToAddress", "")
        self.Notify_IfServerChan = ConfigItem(
            "Notify", "IfServerChan", False, BoolValidator()
        )
        self.Notify_ServerChanKey = ConfigItem("Notify", "ServerChanKey", "")
        self.Notify_CustomWebhooks = MultipleConfig([Webhook])

        super().__init__()

    def getInfrastName(self) -> str:
        if self.get("Info", "InfrastMode") != "Custom":
            return "未使用自定义基建模式"

        infrast_data = json.loads(self.get("Data", "CustomInfrast"))
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

    def getInfrastIndex(self) -> str:
        if self.get("Info", "InfrastMode") != "Custom":
            return "-1"

        infrast_data = json.loads(self.get("Data", "CustomInfrast"))
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

        return self.get("Data", "InfrastIndex") or "0"

    def getTags(self) -> str:
        """生成用户标签列表。"""

        tags: list[dict[str, str]] = []

        if not self.get("Data", "IfPassCheck"):
            tags.append({"text": "人工排查未通过", "color": "red"})

        if (
            datetime.strptime(self.get("Data", "LastProxyDate"), "%Y-%m-%d").date()
            == datetime.now(tz=UTC4).date()
        ):
            tags.append(
                {
                    "text": f"日常：已代理{self.get('Data', 'ProxyTimes')}次",
                    "color": "green",
                }
            )
        else:
            tags.append({"text": "日常：未代理", "color": "orange"})

        if self.get("Info", "IfSkland"):
            if (
                datetime.strptime(self.get("Data", "LastSklandDate"), "%Y-%m-%d").date()
                == datetime.now(tz=UTC8).date()
            ):
                tags.append({"text": "森空岛：已签到", "color": "green"})
            else:
                tags.append({"text": "森空岛：未签到", "color": "orange"})
        else:
            tags.append({"text": "森空岛：禁用", "color": "red"})

        remained_day = self.get("Info", "RemainedDay")
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

        infrast_mode = self.get("Info", "InfrastMode")
        if self.get("Task", "IfInfrast"):
            if infrast_mode == "Normal":
                infrast_text = "基建：常规"
            elif infrast_mode == "Rotation":
                infrast_text = "基建：轮换"
            elif infrast_mode == "Custom":
                infrast_name = self.getInfrastName()
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
            stage_key: self.get_stage_zh(self.get("Info", stage_key))
            for stage_key in MAA_STAGE_KEY[2:]
        }
        tag_color = "blue"
        if self.get("Info", "StageMode") != "Fixed":
            try:
                plan = self.related_config["PlanConfig"][
                    uuid.UUID(self.get("Info", "StageMode"))
                ]
            except Exception:
                plan = None
            if hasattr(plan, "get_current_info"):
                plan_data = {
                    stage_key: self.get_stage_zh(plan.get_current_info(stage_key).getValue())
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
            tags.append(
                {"text": f"剩余：{plan_data['Stage_Remain']}", "color": tag_color}
            )

        notes = self.get("Info", "Notes")
        tags.append(
            {
                "text": f"备注：{notes}" if len(notes) <= 20 else f"备注：{notes[:20]}...",
                "color": "pink",
            }
        )

        return json.dumps(tags, ensure_ascii=False)

    @staticmethod
    def get_stage_zh(stage: str) -> str:
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


class MaaConfig(ConfigBase):
    """MAA 脚本配置。"""

    related_config: dict[str, MultipleConfig] = {}

    def __init__(self) -> None:
        self.Info_Name = ConfigItem("Info", "Name", "新 MAA 脚本")
        self.Info_Path = ConfigItem("Info", "Path", str(Path.cwd()), FolderValidator())

        self.Emulator_Id = ConfigItem(
            "Emulator",
            "Id",
            "-",
            MultipleUIDValidator("-", self.related_config, "EmulatorConfig"),
        )
        self.Emulator_Index = ConfigItem("Emulator", "Index", "-")

        self.Run_TaskTransitionMethod = ConfigItem(
            "Run",
            "TaskTransitionMethod",
            "ExitEmulator",
            OptionsValidator(["NoAction", "ExitGame", "ExitEmulator"]),
        )
        self.Run_ProxyTimesLimit = ConfigItem(
            "Run", "ProxyTimesLimit", 0, RangeValidator(0, 9999)
        )
        self.Run_RunTimesLimit = ConfigItem(
            "Run", "RunTimesLimit", 3, RangeValidator(1, 9999)
        )
        self.Run_AnnihilationTimeLimit = ConfigItem(
            "Run", "AnnihilationTimeLimit", 40, RangeValidator(1, 9999)
        )
        self.Run_RoutineTimeLimit = ConfigItem(
            "Run", "RoutineTimeLimit", 10, RangeValidator(1, 9999)
        )
        self.Run_AnnihilationAvoidWaste = ConfigItem(
            "Run", "AnnihilationAvoidWaste", False, BoolValidator()
        )

        self.UserData = MultipleConfig([MaaUserConfig])

        super().__init__()


def bind_related_config(config_root: object) -> None:
    """绑定运行时关联配置，避免依赖主程序中的同名类。"""

    if hasattr(config_root, "EmulatorConfig"):
        MaaConfig.related_config["EmulatorConfig"] = getattr(
            config_root, "EmulatorConfig"
        )
    if hasattr(config_root, "PlanConfig"):
        MaaUserConfig.related_config["PlanConfig"] = getattr(config_root, "PlanConfig")


__all__ = ["Config", "MaaConfig", "MaaUserConfig", "bind_related_config"]
