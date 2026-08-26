from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any


COURSE_DIRECTORY = "课程表"
SCHEDULE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def load_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SystemExit(f"无法读取{label}：{path}：{exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"{label}必须是 JSON 对象：{path}")
    return data


def schedule_id_for(filename: str, used_ids: set[str]) -> str:
    stem = Path(filename).stem
    candidate = re.sub(r"[^A-Za-z0-9_-]+", "-", stem).strip("-_")
    if not candidate:
        candidate = f"schedule-{hashlib.sha256(filename.encode('utf-8')).hexdigest()[:12]}"
    candidate = candidate[:64]
    if candidate not in used_ids and SCHEDULE_ID_PATTERN.fullmatch(candidate):
        return candidate

    suffix_seed = hashlib.sha256(filename.encode("utf-8")).hexdigest()
    for length in range(6, 25, 2):
        suffix = suffix_seed[:length]
        candidate_with_suffix = f"{candidate[: 64 - len(suffix) - 1]}-{suffix}"
        if candidate_with_suffix not in used_ids:
            return candidate_with_suffix
    raise SystemExit(f"无法为课程表生成唯一标识：{filename}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="将指定课程表加入 ClassWidgets 集控清单")
    parser.add_argument("--schedule-file", required=True, help="课程表目录顶层的 JSON 文件名")
    parser.add_argument("--schedule-name", default="", help="设置页显示名称；留空时使用文件名")
    parser.add_argument("--course-dir", default=COURSE_DIRECTORY)
    parser.add_argument("--manifest", default="manifest.json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    selected_name = str(args.schedule_file).strip()
    selected_relative = Path(selected_name)
    if (
        not selected_name
        or selected_relative.is_absolute()
        or len(selected_relative.parts) != 1
        or selected_relative.suffix.lower() != ".json"
    ):
        raise SystemExit("请选择“课程表”文件夹顶层的一个 .json 文件名，不能使用路径或其他扩展名。")

    course_dir = Path(args.course_dir)
    schedule_path = course_dir / selected_relative.name
    if not schedule_path.is_file():
        raise SystemExit(f"课程表不存在：{selected_relative.name}")

    schedule = load_json_object(schedule_path, "课程表")
    meta = schedule.get("meta")
    if not isinstance(meta, dict):
        raise SystemExit(f"课程表缺少 meta 对象：{schedule_path}")
    schema_version = meta.get("version")
    if isinstance(schema_version, bool) or not isinstance(schema_version, int):
        raise SystemExit(f"课程表 meta.version 必须是整数：{schedule_path}")

    manifest_path = Path(args.manifest)
    manifest = load_json_object(manifest_path, "集控清单")
    if manifest.get("schemaVersion") != 1:
        raise SystemExit("集控清单 schemaVersion 必须为 1")

    raw_entries = manifest.get("schedules")
    if raw_entries is None:
        legacy_entry = manifest.get("schedule")
        raw_entries = [legacy_entry] if isinstance(legacy_entry, dict) else []
    if not isinstance(raw_entries, list):
        raise SystemExit("集控清单 schedules 必须是数组")

    target_url = f"{course_dir.as_posix()}/{selected_relative.name}"
    normalized_entries: list[dict[str, Any]] = []
    used_ids: set[str] = set()
    existing_entry: dict[str, Any] | None = None
    for raw_entry in raw_entries:
        if not isinstance(raw_entry, dict):
            raise SystemExit("集控清单 schedules 中包含非对象项")
        entry = dict(raw_entry)
        if str(entry.get("url", "")) == target_url:
            existing_entry = entry
            continue
        entry_id = str(entry.get("id", ""))
        if not SCHEDULE_ID_PATTERN.fullmatch(entry_id) or entry_id in used_ids:
            raise SystemExit("已有课程表清单项的 id 无效或重复")
        used_ids.add(entry_id)
        normalized_entries.append(entry)

    existing_id = str(existing_entry.get("id", "")) if existing_entry else ""
    schedule_id = (
        existing_id
        if SCHEDULE_ID_PATTERN.fullmatch(existing_id) and existing_id not in used_ids
        else schedule_id_for(selected_name, used_ids)
    )
    display_name = str(args.schedule_name).strip() or str(
        existing_entry.get("name", "") if existing_entry else ""
    ).strip() or selected_relative.stem
    content = schedule_path.read_bytes()
    normalized_entries.append(
        {
            "id": schedule_id,
            "name": display_name,
            "url": target_url,
            "sha256": hashlib.sha256(content).hexdigest(),
            "scheduleSchemaVersion": schema_version,
        }
    )

    run_id = os.environ.get("GITHUB_RUN_ID", "manual")
    updated_manifest = dict(manifest)
    updated_manifest.pop("schedule", None)
    updated_manifest["schedules"] = normalized_entries
    updated_manifest["policyVersion"] = f"schedule-add-{run_id}"
    manifest_path.write_text(
        json.dumps(updated_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"已加入课程表：{selected_relative.name}；清单标识：{schedule_id}")


if __name__ == "__main__":
    main()
