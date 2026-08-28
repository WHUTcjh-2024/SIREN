"""Validate and transactionally import an aggregated live teaching workspace."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.core.config import get_settings
from backend.schemas.teacher import TeacherActor
from backend.services.teacher_workspace import TeacherWorkspaceStore


def main() -> int:
    parser = argparse.ArgumentParser(description="导入真实教学聚合数据")
    parser.add_argument("workspace", type=Path, help="符合 TeacherWorkspaceData 的 UTF-8 JSON")
    parser.add_argument("--db", type=Path, help="目标 SQLite 文件；默认使用运行配置")
    args = parser.parse_args()
    settings = get_settings()
    payload = json.loads(args.workspace.read_text(encoding="utf-8"))
    store = TeacherWorkspaceStore(
        db_file=(args.db or settings.teacher_workspace_db_file).resolve(),
        seed_file=settings.teacher_workspace_seed_file,
        legacy_file=settings.teacher_workspace_file,
    )
    current = store.read()
    profile, _, revision = store.import_live_workspace(
        payload,
        TeacherActor(id="workspace-import", display_name="数据导入工具"),
        current["revision"],
    )
    print(json.dumps({"revision": revision, **profile}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
