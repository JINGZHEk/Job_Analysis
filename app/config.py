"""配置加载与常量定义。"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

# 项目根目录（本文件位于 app/ 下）
ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT_DIR / "config"
DATA_DIR = ROOT_DIR / "data"

_DEFAULT_CONFIG_PATH = CONFIG_DIR / "default.json"


def _deep_merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


class Config:
    def __init__(self, data: dict[str, Any]):
        self._data = data

    def get(self, *keys: str, default: Any = None) -> Any:
        node: Any = self._data
        for k in keys:
            if not isinstance(node, dict) or k not in node:
                return default
            node = node[k]
        return node

    @property
    def raw(self) -> dict:
        return self._data


def load_config(path: str | os.PathLike | None = None) -> Config:
    data: dict = json.loads(_DEFAULT_CONFIG_PATH.read_text(encoding="utf-8"))
    override_path = Path(path) if path else None
    if override_path is None:
        env_path = os.environ.get("JOB_GRAPH_CONFIG")
        if env_path:
            override_path = Path(env_path)
    if override_path and override_path.exists():
        override = json.loads(override_path.read_text(encoding="utf-8"))
        data = _deep_merge(data, override)
    return Config(data)
