from __future__ import annotations

import shutil
import copy
from datetime import datetime
from pathlib import Path
from typing import Any

from app.core.script_types import is_script_config_compatible_with_type_key
from app.models.ConfigBase import MultipleConfig
from app.models.task import UserItem
from app.plugins import ScriptAdapterHooks, ScriptAdapterRuntime
from app.plugins.schema_utils import (
    SchemaDecorationContext,
    set_schema_field_label,
    set_schema_field_options,
    set_schema_field_state,
    set_schema_group_label,
)
from app.utils import get_logger
from app.utils.constants import TASK_MODE_ZH
from .schema import MaaUserConfig

logger = get_logger("MAA 适配")


def _build_infrast_plan_options(config_data: dict[str, Any]) -> list[dict[str, str]]:
    data_group = config_data.get("Data")
    if not isinstance(data_group, dict):
        return []
    custom_infrast = data_group.get("CustomInfrast")
    if not isinstance(custom_infrast, dict):
        return []
    plans = custom_infrast.get("plans")
    if not isinstance(plans, list):
        return []
    options: list[dict[str, str]] = []
    for index, plan in enumerate(plans):
        if isinstance(plan, dict):
            label = str(plan.get("name") or f"排班 {index + 1}")
        else:
            label = f"排班 {index + 1}"
        options.append({"label": label, "value": str(index)})
    return options


class MaaAdapterHooks(ScriptAdapterHooks):
    """MAA 专项适配钩子。"""

    async def decorate_script_schema(
        self,
        schema: dict[str, Any],
        config_data: dict[str, Any],
        ctx: SchemaDecorationContext,
    ) -> dict[str, Any]:
        group_labels = {
            "Info": "基础信息",
            "Emulator": "模拟器设置",
            "Run": "运行设置",
        }
        field_labels = {
            "Info.Name": "脚本名称",
            "Info.Path": "MAA 根目录",
            "Emulator.Id": "模拟器",
            "Emulator.Index": "多开实例",
            "Run.TaskTransitionMethod": "任务切换方式",
            "Run.ProxyTimesLimit": "代理次数限制",
            "Run.RunTimesLimit": "运行次数限制",
            "Run.AnnihilationTimeLimit": "剿灭时间限制（分钟）",
            "Run.RoutineTimeLimit": "日常时间限制（分钟）",
            "Run.AnnihilationAvoidWaste": "剿灭避免浪费理智",
        }

        for group_key, label in group_labels.items():
            set_schema_group_label(schema, group_key, label)
        for field_key, label in field_labels.items():
            set_schema_field_label(schema, field_key, label)

        set_schema_field_state(
            schema,
            "Info.Path",
            placeholder="请选择 MAA 的安装目录",
            size="large",
        )
        set_schema_field_options(schema, "Emulator.Id", await ctx.get_emulator_combox())

        selected_emulator = ""
        emulator_group = config_data.get("Emulator")
        if isinstance(emulator_group, dict):
            selected_emulator = str(emulator_group.get("Id") or "")

        emulator_index_options = [{"label": "未选择", "value": "-"}]
        if selected_emulator and selected_emulator != "-":
            try:
                scanned_options = await ctx.get_emulator_devices_combox(selected_emulator)
                if scanned_options:
                    emulator_index_options = scanned_options
            except Exception as exc:
                logger.warning(f"获取 MAA 模拟器多开实例失败: {type(exc).__name__}: {exc}")

        set_schema_field_options(schema, "Emulator.Index", emulator_index_options)
        set_schema_field_state(
            schema,
            "Emulator.Index",
            help_text="选择多开序号；若列表为空，可保持为“未选择”后由运行时自动处理。",
        )

        return schema

    async def decorate_user_schema(
        self,
        schema: dict[str, Any],
        config_data: dict[str, Any],
        ctx: SchemaDecorationContext,
    ) -> dict[str, Any]:
        group_labels = {
            "Info": "基础信息",
            "Task": "任务开关",
            "Notify": "通知设置",
            "Data": "运行数据",
        }
        field_labels = {
            "Info.Name": "用户名称",
            "Info.Id": "用户 ID",
            "Info.Password": "密码",
            "Info.Mode": "展示模式",
            "Info.StageMode": "关卡模式",
            "Info.Server": "服务器",
            "Info.Status": "启用用户",
            "Info.RemainedDay": "剩余天数",
            "Info.Annihilation": "剿灭设置",
            "Info.InfrastMode": "基建模式",
            "Info.InfrastName": "自定义基建名称",
            "Info.InfrastIndex": "当前班次索引",
            "Info.Notes": "备注",
            "Info.MedicineNumb": "吃理智药数量",
            "Info.SeriesNumb": "连战次数",
            "Info.Stage": "主关卡",
            "Info.Stage_1": "备选关卡 1",
            "Info.Stage_2": "备选关卡 2",
            "Info.Stage_3": "备选关卡 3",
            "Info.Stage_Remain": "剩余理智关卡",
            "Info.IfSkland": "森空岛签到",
            "Info.SklandToken": "森空岛 Token",
            "Info.Tag": "用户标签",
            "Data.LastProxyDate": "上次代理日期",
            "Data.LastSklandDate": "上次森空岛签到日期",
            "Data.ProxyTimes": "今日代理次数",
            "Data.IfPassCheck": "人工排查通过",
            "Data.CustomInfrast": "自定义基建 JSON",
            "Data.InfrastIndex": "自定义基建排班",
            "Task.IfStartUp": "自动启动",
            "Task.IfFight": "理智作战",
            "Task.IfInfrast": "基建换班",
            "Task.IfRecruit": "公开招募",
            "Task.IfMall": "信用收支",
            "Task.IfAward": "领取奖励",
            "Task.IfRoguelike": "肉鸽",
            "Task.IfReclamation": "生息演算",
            "Notify.Enabled": "启用通知",
            "Notify.IfSendStatistic": "发送统计信息",
            "Notify.IfSendSixStar": "发送高资喜报",
            "Notify.IfSendMail": "邮件通知",
            "Notify.ToAddress": "收件邮箱",
            "Notify.IfServerChan": "Server酱通知",
            "Notify.ServerChanKey": "Server酱 SENDKEY",
        }

        for group_key, label in group_labels.items():
            set_schema_group_label(schema, group_key, label)
        for field_key, label in field_labels.items():
            set_schema_field_label(schema, field_key, label)

        set_schema_field_options(schema, "Info.StageMode", await ctx.get_plan_combox())
        set_schema_field_options(
            schema,
            "Info.InfrastMode",
            [
                {"label": "常规模式", "value": "Normal"},
                {"label": "一键轮休", "value": "Rotation"},
                {"label": "自定义基建", "value": "Custom"},
            ],
        )
        set_schema_field_options(
            schema,
            "Info.SeriesNumb",
            [
                {"label": "AUTO", "value": "0"},
                {"label": "1", "value": "1"},
                {"label": "2", "value": "2"},
                {"label": "3", "value": "3"},
                {"label": "4", "value": "4"},
                {"label": "5", "value": "5"},
                {"label": "6", "value": "6"},
                {"label": "不切换", "value": "-1"},
            ],
        )

        stage_options = await ctx.get_stage_info("User")
        if not isinstance(stage_options, list):
            stage_options = []
        stage_remain_options = copy.deepcopy(stage_options)
        for option in stage_remain_options:
            if isinstance(option, dict) and option.get("value") == "-":
                option["label"] = "不选择"

        for field_key in ("Info.Stage", "Info.Stage_1", "Info.Stage_2", "Info.Stage_3"):
            set_schema_field_options(
                schema,
                field_key,
                stage_options,
                allow_custom=True,
            )
            set_schema_field_state(
                schema,
                field_key,
                placeholder="选择或输入自定义关卡",
            )

        set_schema_field_options(
            schema,
            "Info.Stage_Remain",
            stage_remain_options,
            allow_custom=True,
        )
        set_schema_field_state(
            schema,
            "Info.Stage_Remain",
            placeholder="选择或输入自定义关卡",
            help_text="选择“不选择”时，将不使用剩余理智关卡。",
        )

        info_group = config_data.get("Info")
        if not isinstance(info_group, dict):
            info_group = {}
        stage_mode = str(info_group.get("StageMode") or "Fixed")
        if stage_mode != "Fixed":
            plan_help = "当前由计划表控制，请前往计划表修改。"
            for field_key in (
                "Info.MedicineNumb",
                "Info.SeriesNumb",
                "Info.Stage",
                "Info.Stage_1",
                "Info.Stage_2",
                "Info.Stage_3",
                "Info.Stage_Remain",
            ):
                set_schema_field_state(
                    schema,
                    field_key,
                    readonly=True,
                    help_text=plan_help,
                )

        infrast_mode = str(info_group.get("InfrastMode") or "Normal")
        infrast_options = _build_infrast_plan_options(config_data)
        if infrast_options:
            set_schema_field_options(schema, "Data.InfrastIndex", infrast_options)

        if infrast_mode != "Custom":
            custom_help = "当前不是自定义基建模式，此区域仅保留已保存数据。"
            set_schema_field_state(
                schema,
                "Data.InfrastIndex",
                readonly=True,
                help_text=custom_help,
            )
            set_schema_field_state(
                schema,
                "Data.CustomInfrast",
                readonly=True,
                help_text=custom_help,
                rows=12,
                size="large",
            )
        else:
            infrast_help = "可直接粘贴自定义基建配置 JSON，保存后会按当前排班生效。"
            if not infrast_options:
                infrast_help = "请先在下方填写有效的自定义基建 JSON，保存后即可选择排班。"
            set_schema_field_state(
                schema,
                "Data.InfrastIndex",
                help_text=infrast_help,
            )
            set_schema_field_state(
                schema,
                "Data.CustomInfrast",
                help_text="直接编辑或粘贴完整的自定义基建 JSON。",
                rows=12,
                size="large",
            )

        set_schema_field_state(
            schema,
            "Info.Tag",
            help_text="运行时自动生成，仅用于展示。",
        )
        set_schema_field_state(
            schema,
            "Info.InfrastName",
            help_text="运行时根据自定义基建 JSON 自动解析。",
        )
        return schema

    async def check(self, runtime: ScriptAdapterRuntime) -> str:
        from app.core.config import Config

        if runtime.mode not in ("AutoProxy", "ManualReview", "ScriptConfig"):
            return "不支持的任务模式，请检查任务配置！"

        script_config = Config.ScriptConfig[runtime.script_uid]
        if not is_script_config_compatible_with_type_key(script_config, "MAA"):
            return "脚本配置类型错误, 不是 MAA 脚本类型"

        if script_config.get("Emulator", "Id") == "-" or script_config.get(
            "Emulator", "Index"
        ) in ("", "-"):
            return "未完成模拟器配置, 请检查脚本配置中的模拟器设置！"

        if not (Path(script_config.get("Info", "Path")) / "MAA.exe").exists():
            return "MAA.exe 文件不存在，请检查 MAA 路径设置！"

        if not (
            (Path(script_config.get("Info", "Path")) / "config/gui.json").exists()
            and (Path(script_config.get("Info", "Path")) / "config/gui.new.json").exists()
        ):
            return "MAA 配置文件不存在，请检查 MAA 路径设置或先启动 MAA 生成配置文件！"

        if runtime.mode != "ScriptConfig" and not (
            Path.cwd() / f"data/{runtime.script_info.script_id}/Default/ConfigFile"
        ).exists():
            return "未完成 MAA 全局配置，请先配置 MAA！"

        return "Pass"

    async def prepare(self, runtime: ScriptAdapterRuntime) -> None:
        from app.core.config import Config
        from app.core.emulator_manager import EmulatorManager

        script_config = Config.ScriptConfig[runtime.script_uid]
        await script_config.lock()

        runtime.script_config = script_config
        runtime.user_config = MultipleConfig([MaaUserConfig])
        await runtime.user_config.load(await script_config.UserData.toDict())
        logger.success(f"{runtime.script_info.script_id} 已锁定, MAA 配置提取完成")

        maa_set_path = Path(script_config.get("Info", "Path")) / "config"
        temp_path = Path.cwd() / f"data/{runtime.script_info.script_id}/Temp"
        runtime.extra["maa_set_path"] = maa_set_path
        runtime.extra["temp_path"] = temp_path
        runtime.extra["emulator_manager"] = await EmulatorManager.get_emulator_instance(
            script_config.get("Emulator", "Id")
        )

        temp_path.mkdir(parents=True, exist_ok=True)
        if maa_set_path.exists():
            shutil.copytree(maa_set_path, temp_path, dirs_exist_ok=True)

        if runtime.mode == "ScriptConfig":
            runtime.script_info.user_list = [
                UserItem(
                    user_id=runtime.task_info.user_id or "Default",
                    name="",
                    status="等待",
                )
            ]
        else:
            runtime.script_info.user_list = [
                UserItem(
                    user_id=str(uid),
                    name=config.get("Info", "Name"),
                    status="等待",
                )
                for uid, config in runtime.user_config.items()
                if config.get("Info", "Status")
                and config.get("Info", "RemainedDay") != 0
            ]

        logger.info(
            f"用户列表加载完成, 已筛选用户数: {len(runtime.script_info.user_list)}"
        )

    def run_auto_proxy(self, runtime: ScriptAdapterRuntime, user_index: int):
        from .maa_task.AutoProxy import AutoProxyTask

        _ = user_index
        return AutoProxyTask(
            runtime.script_info,
            runtime.script_config,
            runtime.user_config,
            runtime.extra.get("emulator_manager"),
        )

    def run_manual_review(self, runtime: ScriptAdapterRuntime, user_index: int):
        from .maa_task.ManualReview import ManualReviewTask

        _ = user_index
        return ManualReviewTask(
            runtime.script_info,
            runtime.script_config,
            runtime.user_config,
            runtime.extra.get("emulator_manager"),
        )

    def run_script_config(self, runtime: ScriptAdapterRuntime, user_index: int):
        from .maa_task.ScriptConfig import ScriptConfigTask

        _ = user_index
        return ScriptConfigTask(
            runtime.script_info,
            runtime.script_config,
            runtime.user_config,
            runtime.extra.get("emulator_manager"),
        )

    async def finalize(self, runtime: ScriptAdapterRuntime) -> None:
        from app.core.config import Config
        from app.services.notification import Notify
        from .maa_task.tools.notify import push_notification

        if runtime.check_result != "Pass":
            runtime.script_info.status = "异常"
            return

        script_config = runtime.script_config
        if script_config is None:
            runtime.script_info.status = "异常"
            return

        logger.info("MAA 主任务已结束, 开始执行后续操作")
        await script_config.unlock()
        logger.success(f"已解锁脚本配置 {runtime.script_info.script_id}")

        if runtime.mode in ("AutoProxy", "ManualReview"):
            emulator_manager = runtime.extra.get("emulator_manager")
            if emulator_manager is not None:
                await emulator_manager.close(script_config.get("Emulator", "Index"))

            await script_config.UserData.load(await runtime.user_config.toDict())

            error_user = [
                user.name for user in runtime.script_info.user_list if user.status == "异常"
            ]
            over_user = [
                user.name for user in runtime.script_info.user_list if user.status == "完成"
            ]
            wait_user = [
                user.name for user in runtime.script_info.user_list if user.status == "等待"
            ]

            title = (
                f"{datetime.now().strftime('%m-%d')} | "
                f"{runtime.script_info.name or '空白'}的{TASK_MODE_ZH[runtime.mode]}任务报告"
            )
            result = {
                "title": f"{TASK_MODE_ZH[runtime.mode]}任务报告",
                "script_name": runtime.script_info.name or "空白",
                "start_time": runtime.begin_time,
                "end_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "completed_count": len(over_user),
                "uncompleted_count": len(error_user) + len(wait_user),
                "result": runtime.script_info.result,
            }

            await Notify.push_plyer(
                title.replace("报告", "已完成！"),
                (
                    f"已完成用户数: {len(over_user)}, "
                    f"未完成用户数: {len(error_user) + len(wait_user)}"
                ),
                (
                    f"已完成用户数: {len(over_user)}, "
                    f"未完成用户数: {len(error_user) + len(wait_user)}"
                ),
                10,
            )
            try:
                await push_notification("代理结果", title, result, None)
            except Exception as error:
                logger.exception(f"推送代理结果时出现异常: {error}")
                await Config.send_websocket_message(
                    id=runtime.task_info.task_id,
                    type="Info",
                    data={"Error": f"推送代理结果时出现异常: {error}"},
                )

        maa_set_path: Path | None = runtime.extra.get("maa_set_path")
        temp_path: Path | None = runtime.extra.get("temp_path")
        if maa_set_path is not None and temp_path is not None:
            if temp_path.exists():
                shutil.rmtree(maa_set_path, ignore_errors=True)
                shutil.copytree(temp_path, maa_set_path, dirs_exist_ok=True)
            shutil.rmtree(temp_path, ignore_errors=True)

        runtime.script_info.status = "完成"

    async def on_crash(self, runtime: ScriptAdapterRuntime, error: Exception) -> None:
        from app.core.config import Config

        runtime.script_info.status = "异常"
        logger.exception(f"MAA 任务出现异常: {error}")
        await Config.send_websocket_message(
            id=runtime.task_info.task_id,
            type="Info",
            data={"Error": f"MAA 任务出现异常: {error}"},
        )
