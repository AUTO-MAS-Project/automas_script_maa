from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from app.core.script_types import is_script_config_compatible_with_type_key
from app.models.ConfigBase import MultipleConfig
from app.models.task import UserItem
from app.plugins import ScriptAdapterHooks, ScriptAdapterRuntime
from app.utils import get_logger
from app.utils.constants import TASK_MODE_ZH
from .schema import MaaUserConfig

logger = get_logger("MAA 适配")


class MaaAdapterHooks(ScriptAdapterHooks):
    """MAA 专项适配钩子。"""

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
