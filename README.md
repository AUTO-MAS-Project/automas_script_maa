# automas_plugin_script_maa

`script_MAA` 是通过 `scripts/plugin_tool.py` 生成后接入的 MAA 脚本桥接插件。

它会在插件生命周期内注册 `MAA` 脚本类型 provider，并复用宿主已有的 `MaaConfig`、`MaaUserConfig` 与 `builtin:maa` 编辑页。
