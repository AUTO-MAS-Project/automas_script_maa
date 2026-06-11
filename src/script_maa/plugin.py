from __future__ import annotations

from app.plugins import ScriptAdapterDefinition, ScriptAdapterPlugin

from .adapter import MaaAdapterHooks
from .options import resolve_notification_channels, resolve_plan_combox, resolve_stage_info
from .schema import MaaConfigModel, MaaUserConfigModel

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

    wants = "notify"

    def build_script_adapters(self) -> list[ScriptAdapterDefinition]:
        return [
            ScriptAdapterDefinition(
                type_key="MAA",
                display_name="MAA脚本",
                hooks_factory=MaaAdapterHooks,
                script_model=MaaConfigModel,
                user_model=MaaUserConfigModel,
                script_class_name="MaaConfig",
                user_class_name="MaaUserConfig",
                related_bindings={
                    "EmulatorConfig": "EmulatorConfig",
                    "PlanConfig": "PlanConfig",
                },
                supported_modes=("AutoProxy", "ManualReview", "ScriptConfig"),
                icon="MAA",
                editor_kind="plugin:script_maa",
                metadata={"framework": "script_adapter"},
                options_providers={
                    "notification_channels": resolve_notification_channels,
                    "plan_combox": resolve_plan_combox,
                    "stage_info": resolve_stage_info,
                },
            )
        ]
