#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
诊断包导出：版本、脱敏配置摘要、最近日志片段 — 便于用户反馈 [ERR-xxxxxxxxxx] 问题时附带。
"""

from __future__ import annotations

import json
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.app_paths import get_documents_app_dir, get_project_root
from core.log_manager import get_log_manager


def _redact_config(obj: Any) -> Any:
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            lk = str(k).lower()
            if any(x in lk for x in ("api_key", "secret", "token", "password", "credential")):
                out[k] = "***REDACTED***"
            else:
                out[k] = _redact_config(v)
        return out
    if isinstance(obj, list):
        return [_redact_config(x) for x in obj]
    return obj


def _read_text_safe(path: Path, max_bytes: int = 256_000) -> str:
    try:
        data = path.read_bytes()[:max_bytes]
        return data.decode("utf-8", errors="replace")
    except OSError:
        return ""


def _latest_log_files(log_dir: Path, limit: int = 2) -> List[Path]:
    if not log_dir.is_dir():
        return []
    logs = sorted(
        [p for p in log_dir.iterdir() if p.suffix in (".log", ".jsonl") and p.is_file()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return logs[:limit]


def export_diagnostic_zip(
    dest: Path,
    *,
    project_version: Optional[str] = None,
    extra_log_paths: Optional[List[Path]] = None,
) -> Path:
    """写入 zip 并返回路径。"""
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)

    root = get_project_root()
    meta: Dict[str, Any] = {
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "project_root": str(root),
    }
    if project_version:
        meta["version"] = project_version

    cfg_dev = root / "config" / "config.yml"
    cfg_user = get_documents_app_dir() / "config.yml"
    config_snapshot = ""
    for candidate in (cfg_user, cfg_dev):
        if candidate.is_file():
            try:
                import yaml

                raw = yaml.safe_load(candidate.read_text(encoding="utf-8"))
                meta["config_source"] = str(candidate)
                config_snapshot = json.dumps(_redact_config(raw or {}), ensure_ascii=False, indent=2)
            except Exception as e:
                config_snapshot = f"(读取配置失败: {e})"
            break

    lm = get_log_manager()
    log_dir = Path(lm.log_dir) if lm else get_documents_app_dir() / "logs"
    log_excerpt = ""
    for lf in (extra_log_paths or []) + _latest_log_files(log_dir):
        if not lf or not Path(lf).is_file():
            continue
        log_excerpt += f"\n\n===== {lf} (尾部) =====\n"
        text = _read_text_safe(Path(lf))
        log_excerpt = log_excerpt + text[-40_000:]
        break

    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("meta.json", json.dumps(meta, ensure_ascii=False, indent=2))
        if config_snapshot:
            zf.writestr("config_redacted.json", config_snapshot)
        if log_excerpt:
            zf.writestr("log_tail.txt", log_excerpt)

    return dest
