from __future__ import annotations

from typing import TYPE_CHECKING

from app.core import Config as RuntimeConfig
from app.core.script_types import ScriptTypeProvider, script_type_registry

from .schema import MaaConfig, MaaUserConfig, bind_related_config

if TYPE_CHECKING:
    from app.plugins import PluginContext


DEFAULT_INSTANCE = {
    "name": "script_MAA 脚本桥接",
    "enabled": True,
    "config": {},
}

SCRIPT_TYPE_BINDINGS = [
    {
        "type_key": "MAA",
        "display_name": "MAA脚本",
        "script_config_class_name": "MaaConfig",
    }
]


class Plugin:
    """负责把外部 MAA 运行实现桥接为脚本类型 provider。"""

    def __init__(self, ctx: "PluginContext") -> None:
        self.ctx = ctx

    async def on_start(self) -> None:
        from .maa_task.manager import MaaManager

        bind_related_config(RuntimeConfig)
        provider = ScriptTypeProvider(
            type_key="MAA",
            display_name="MAA脚本",
            script_config_class=MaaConfig,
            user_config_class=MaaUserConfig,
            supported_modes=("AutoProxy", "ManualReview", "ScriptConfig"),
            manager_factory=MaaManager,
            icon="MAA",
            editor_kind="plugin:script_maa",
        )
        script_type_registry.register(provider, owner=self.ctx.instance_id)
        self.ctx.logger.info("已注册外部 MAA 脚本类型 provider")

    async def on_stop(self, reason: str) -> None:
        _ = reason
        removed = script_type_registry.unregister_by_owner(self.ctx.instance_id)
        self.ctx.logger.info(f"已注销外部 MAA 脚本类型 provider: {removed}")

    async def on_unload(self) -> None:
        removed = script_type_registry.unregister_by_owner(self.ctx.instance_id)
        self.ctx.logger.info(f"已卸载外部 MAA 脚本类型 provider: {removed}")
