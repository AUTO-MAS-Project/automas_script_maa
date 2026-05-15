from __future__ import annotations

from app.plugins import ScriptAdapterDefinition, ScriptAdapterPlugin

from .adapter import MaaAdapterHooks
from .schema import MaaConfig, MaaUserConfig, bind_related_config

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


class Plugin(ScriptAdapterPlugin):
    """把 MAA 适配包注册为统一脚本适配插件。"""

    def build_script_adapters(self) -> list[ScriptAdapterDefinition]:
        return [
            ScriptAdapterDefinition(
                type_key="MAA",
                display_name="MAA脚本",
                script_config_class=MaaConfig,
                user_config_class=MaaUserConfig,
                hooks_factory=MaaAdapterHooks,
                supported_modes=("AutoProxy", "ManualReview", "ScriptConfig"),
                icon="MAA",
                editor_kind="plugin:script_maa",
                bind_related_config=bind_related_config,
                metadata={"framework": "script_adapter"},
            )
        ]
