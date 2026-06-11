from __future__ import annotations

import json
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from app.core.script_types import is_script_config_compatible_with_type_key
from app.models.ConfigBase import MultipleConfig
from app.models.task import UserItem
from app.plugins import ScriptAdapterHooks, ScriptAdapterRuntime
from app.plugins.schema_utils import (
    SchemaDecorationContext,
    set_schema_field_options,
    set_schema_field_state,
)
from app.utils import get_logger

from .constants import TASK_MODE_ZH

logger = get_logger("MAA 适配")


def _get_notify_service(runtime: ScriptAdapterRuntime) -> Any | None:
    if runtime.plugin_context is None:
        return None
    return runtime.plugin_context.get("notify")


def _get_notify_channels(script_config: Any | None) -> list[str] | None:
    if script_config is None:
        return []
    try:
        raw_channels = script_config.get("Notify", "Channels")
    except Exception:
        return []
    if not isinstance(raw_channels, list):
        return []

    channels: list[str] = []
    seen: set[str] = set()
    for item in raw_channels:
        name = str(item or "").strip()
        if not name or name in seen:
            continue
        if name == "all":
            return None
        seen.add(name)
        channels.append(name)
    return channels


async def _push_system_notification(
    notify_service: Any | None,
    *,
    title: str,
    message: str,
    ticker: str,
    timeout: int,
    channels: list[str] | None = None,
) -> bool:
    if channels == []:
        return True
    if notify_service is None:
        return False

    try:
        if channels is not None and callable(getattr(notify_service, "send_payload", None)):
            result = await notify_service.send_payload(
                {
                    "kind": "system",
                    "title": title,
                    "text": message,
                    "ticker": ticker,
                    "timeout": timeout,
                },
                channels=channels,
            )
            return isinstance(result, dict) and any(bool(ok) for ok in result.values())
        if callable(getattr(notify_service, "send_system", None)):
            return bool(
                await notify_service.send_system(
                    title=title,
                    message=message,
                    ticker=ticker,
                    timeout=timeout,
                )
            )
        return False
    except Exception as exc:
        logger.warning(f"notify 系统通知发送失败，将回退旧实现: {type(exc).__name__}: {exc}")
        return False


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
        _ = ctx

        info_group = config_data.get("Info")
        if not isinstance(info_group, dict):
            info_group = {}
        stage_mode = str(info_group.get("StageMode") or "Fixed")
        if stage_mode != "Fixed":
            plan_help = "当前由计划表控制，请前往计划表修改。"
            for field_key in (
                "Stage.MedicineNumb",
                "Stage.SeriesNumb",
                "Stage.Stage",
                "Stage.Stage_1",
                "Stage.Stage_2",
                "Stage.Stage_3",
                "Stage.Stage_Remain",
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
        return schema

    async def check(self, runtime: ScriptAdapterRuntime) -> str:
        if runtime.mode not in ("AutoProxy", "ManualReview", "ScriptConfig"):
            return "不支持的任务模式，请检查任务配置！"

        script_config = await runtime.build_script_model()
        runtime.script_config = script_config
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
        from app.core.emulator_manager import EmulatorManager

        storage_script_config = runtime.get_storage_script_config()
        await storage_script_config.lock()

        script_config = runtime.script_config or await runtime.build_script_model()
        runtime.script_config = script_config
        provider = runtime._resolve_provider()
        runtime.user_config = MultipleConfig([provider.user_config_class])
        for user_uid, user_model in await runtime.build_user_models():
            uid = uuid.UUID(user_uid)
            runtime.user_config.order.append(uid)
            runtime.user_config.data[uid] = user_model
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
            notify_service=_get_notify_service(runtime),
            notify_channels=_get_notify_channels(runtime.script_config),
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
        notify_service = _get_notify_service(runtime)
        notify_channels = _get_notify_channels(script_config)
        storage_script_config = runtime.get_storage_script_config()
        await storage_script_config.unlock()
        logger.success(f"已解锁脚本配置 {runtime.script_info.script_id}")

        if runtime.mode in ("AutoProxy", "ManualReview"):
            emulator_manager = runtime.extra.get("emulator_manager")
            if emulator_manager is not None:
                await emulator_manager.close(script_config.get("Emulator", "Index"))

            from app.core.script_config_codec import form_to_storage, storage_to_form
            from app.models.plugin_script_config import PluginUserConfig

            provider = runtime._resolve_provider()
            for user_uid, user_model in runtime.user_config.items():
                storage_user = storage_script_config.UserData[user_uid]
                if isinstance(storage_user, PluginUserConfig):
                    user_payload = await user_model.toDict(if_decrypt=False)
                    storage_payload = await form_to_storage(provider, user_payload, "user")
                    await storage_user.set(
                        "PluginData",
                        "Config",
                        json.dumps(storage_payload, ensure_ascii=False),
                    )
                    form_payload = await storage_to_form(provider, storage_payload, "user")
                    user_name = form_payload.get("user_name")
                    if not isinstance(user_name, str) or not user_name.strip():
                        info = form_payload.get("Info")
                        user_name = (
                            info.get("Name")
                            if isinstance(info, dict) and isinstance(info.get("Name"), str)
                            else str(user_uid)
                        )
                    await storage_user.set("Info", "Name", user_name.strip())
                else:
                    await storage_script_config.UserData.load(
                        await runtime.user_config.toDict()
                    )
                    break

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

            system_message = (
                f"已完成用户数: {len(over_user)}, "
                f"未完成用户数: {len(error_user) + len(wait_user)}"
            )
            system_sent = await _push_system_notification(
                notify_service,
                title=title.replace("报告", "已完成！"),
                message=system_message,
                ticker=system_message,
                timeout=10,
                channels=notify_channels,
            )
            if not system_sent and notify_channels is None:
                await Notify.push_plyer(
                    title.replace("报告", "已完成！"),
                    system_message,
                    system_message,
                    10,
                )
            try:
                await push_notification(
                    "代理结果",
                    title,
                    result,
                    None,
                    notify_service=notify_service,
                    notify_channels=notify_channels,
                )
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
