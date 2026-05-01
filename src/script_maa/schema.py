from mas.plugin_config import PluginField
from pydantic import BaseModel, ConfigDict


class Config(BaseModel):
    model_config = ConfigDict(extra="allow")

    reserved: str = PluginField(default="", description="预留字段，当前无需配置")
