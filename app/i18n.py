"""轻量级 i18n 模块 - JSON 翻译文件加载与缓存.

启动时加载 locales/{lang}.json 到内存，提供 get_translations(lang) 函数。
"""

from __future__ import annotations

import json
import os
from typing import Dict

_LOCALES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "locales")
_cache: Dict[str, Dict[str, str]] = {}
SUPPORTED_LANGS = ("zh", "en")
DEFAULT_LANG = (
    "en"  # 国际化优先：默认英文，中文用户走 /zh/ 前缀或 Accept-Language 自动识别
)


def _load(lang: str) -> Dict[str, str]:
    """从磁盘加载翻译文件并缓存."""
    filepath = os.path.join(_LOCALES_DIR, f"{lang}.json")
    if not os.path.exists(filepath):
        return {}
    with open(filepath, "r", encoding="utf-8") as fh:
        return json.load(fh)


def get_translations(lang: str) -> Dict[str, str]:
    """返回指定语言的翻译字典（带内存缓存）.

    如果 lang 不在支持列表中，回退到默认语言。
    """
    if lang not in SUPPORTED_LANGS:
        lang = DEFAULT_LANG
    if lang not in _cache:
        _cache[lang] = _load(lang)
    return _cache[lang]


def t(key: str, lang: str = DEFAULT_LANG) -> str:
    """翻译单个 key，找不到时返回 key 本身."""
    translations = get_translations(lang)
    return translations.get(key, key)


def detect_language(request) -> str:
    """从 FastAPI Request 对象检测语言.

    优先级: URL 前缀 /en/ 或 /zh/ > Cookie 'lang' > Accept-Language header > 默认英文

    设计：默认英文（国际化优先），中文用户通过 Accept-Language(zh-*) 自动识别，
    或显式访问 /zh/ 前缀路由。/en/ 前缀保留以保持向后兼容（以前的英文 URL 仍可访问）。
    """
    # 1. URL 前缀
    path = request.url.path
    if path.startswith("/en/") or path == "/en":
        return "en"
    if path.startswith("/zh/") or path == "/zh":
        return "zh"

    # 2. Cookie
    lang_cookie = request.cookies.get("lang")
    if lang_cookie in SUPPORTED_LANGS:
        return lang_cookie

    # 3. Accept-Language header
    accept_lang = request.headers.get("accept-language", "")
    if accept_lang:
        # 简单解析：检查 zh 是否在 accept-language 中且优先级高于 en
        parts = accept_lang.lower().split(",")
        for part in parts:
            lang_tag = part.split(";")[0].strip()
            if lang_tag.startswith("zh"):
                return "zh"
            if lang_tag.startswith("en"):
                return "en"

    # 4. 默认英文（国际化优先）
    return DEFAULT_LANG
