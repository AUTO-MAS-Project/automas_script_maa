from __future__ import annotations

from functools import lru_cache
from typing import Any

from jinja2 import Environment, PackageLoader


@lru_cache(maxsize=1)
def _get_environment() -> Environment:
    # 创建并缓存插件模板环境。
    return Environment(loader=PackageLoader("script_maa", "templates"))


def render_template(template_name: str, context: dict[str, Any] | None = None) -> str:
    # 加载模板并渲染通知内容。
    template = _get_environment().get_template(template_name)
    return template.render(**(context or {}))
