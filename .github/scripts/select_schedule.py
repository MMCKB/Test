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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="选择一份集控课程表，并将其 yes.id 设为 1，其余课程表设为 0。"
    )
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument(
        "--selected-file",
        help="课程表文件夹内由管理员选择的 JSON 文件名，例如 class-a.json。",
    )
    selection.add_argument(
        "--clear-selection",
        action="store_true",
        help="将所有课程表设为 yes.id=0，仅用于明确清空自动切换选择。",
    )
    parser.add_argument(
        "--course-dir",
        default=COURSE_DIRECTORY,
        help="课程表目录，默认是“课程表”。",
    )
    parser.add_argument(
        "--manifest",
        default="manifest.json",
        help="集控清单路径，默认是仓库根目录的 manifest.json。",
    )
    return parser.parse_args()


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


def update_schedule_yes_id(data: dict[str, Any], enabled: bool, path: Path) -> dict[str, Any]:
    meta = data.get("meta")
    if not isinstance(meta, dict):
        raise SystemExit(f"课程表缺少 meta 对象：{path}")
    yes = data.get("yes")
    if yes is None:
        yes = {}
    if not isinstance(yes, dict):
        raise SystemExit(f"课程表 yes 必须是对象：{path}")
    updated = dict(data)
    updated_yes = dict(yes)
    updated_yes["id"] = 1 if enabled else 0
    updated["yes"] = updated_yes
    return updated


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    temporary = path.with_name(f"{path.name}.tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def main() -> None:
    args = parse_args()
    course_dir = Path(args.course_dir)
    manifest_path = Path(args.manifest)
    if not course_dir.is_dir():
        raise SystemExit(f"课程表目录不存在：{course_dir}")

    schedule_paths = sorted(path for path in course_dir.glob("*.json") if path.is_file())
    if not schedule_paths:
        raise SystemExit(f"课程表目录中没有 JSON 文件：{course_dir}")

    selected_path: Path | None = None
    if not args.clear_selection:
        selected_name = str(args.selected_file or "").strip()
        selected_relative = Path(selected_name)
        if (
            not selected_name
            or selected_relative.is_absolute()
            or len(selected_relative.parts) != 1
            or selected_relative.suffix.lower() != ".json"
        ):
            raise SystemExit("请选择“课程表”文件夹顶层的一个 .json 文件名，不能使用路径或其他扩展名。")
        selected_path = course_dir / selected_relative.name
        if selected_path not in schedule_paths:
            available = "、".join(path.name for path in schedule_paths)
            raise SystemExit(f"所选课程表不存在：{selected_relative.name}。可选文件：{available}")

    # 先完整校验所有文件，避免半途失败时写入部分课程表。
    updated_schedules: dict[Path, dict[str, Any]] = {}
    for path in schedule_paths:
        updated_schedules[path] = update_schedule_yes_id(
            load_json_object(path, "课程表"),
            selected_path is not None and path == selected_path,
            path,
        )

    manifest = load_json_object(manifest_path, "集控清单")
    if manifest.get("schemaVersion") != 1:
        raise SystemExit("集控清单 schemaVersion 必须为 1")

    raw_entries = manifest.get("schedules")
    if raw_entries is None:
        raw_schedule = manifest.get("schedule")
        raw_entries = [raw_schedule] if isinstance(raw_schedule, dict) else []
    if not isinstance(raw_entries, list):
        raise SystemExit("集控清单 schedules 必须是数组")

    existing_by_filename: dict[str, dict[str, Any]] = {}
    for entry in raw_entries:
        if not isinstance(entry, dict):
            raise SystemExit("集控清单 schedules 中包含非对象项")
        url = str(entry.get("url", ""))
        filename = Path(url).name
        if filename:
            existing_by_filename[filename] = dict(entry)

    used_ids: set[str] = set()
    normalized_entries: list[dict[str, Any]] = []
    for path in schedule_paths:
        document = updated_schedules[path]
        existing = existing_by_filename.get(path.name, {})
        schedule_id = str(existing.get("id", ""))
        if not SCHEDULE_ID_PATTERN.fullmatch(schedule_id) or schedule_id in used_ids:
            schedule_id = schedule_id_for(path.name, used_ids)
        used_ids.add(schedule_id)
        content = json.dumps(document, ensure_ascii=False, indent=2).encode("utf-8") + b"\n"
        meta = document["meta"]
        normalized_entries.append(
            {
                "id": schedule_id,
                "name": str(existing.get("name") or path.stem),
                "url": f"{course_dir.as_posix()}/{path.name}",
                "sha256": hashlib.sha256(content).hexdigest(),
                "scheduleSchemaVersion": meta.get("version", 1),
            }
        )

    run_id = os.environ.get("GITHUB_RUN_ID", "manual")
    updated_manifest = dict(manifest)
    updated_manifest.pop("schedule", None)
    updated_manifest["schedules"] = normalized_entries
    updated_manifest["policyVersion"] = f"schedule-select-{run_id}"

    for path, document in updated_schedules.items():
        atomic_write_json(path, document)
    atomic_write_json(manifest_path, updated_manifest)

    if selected_path is None:
        print("已清空自动选择：所有课程表的 yes.id 均为 0。")
    else:
        print(f"已选择课程表：{selected_path.name}")
    print(f"已更新 {len(schedule_paths)} 份课程表的 yes.id，并同步 manifest.json 哈希。")


if __name__ == "__main__":
    main()
