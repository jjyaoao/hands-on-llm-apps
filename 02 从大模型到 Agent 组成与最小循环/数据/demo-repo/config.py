"""配置读取；本仓库只作为 Agent 阅读资料。"""
import json
import os
from pathlib import Path


def load_settings():
    path = Path(os.environ.get("STUDYBOX_CONFIG", "settings.json"))
    if not path.exists():
        return {"course": "大模型应用开发", "timeout": 30}
    return json.loads(path.read_text(encoding="utf-8"))
