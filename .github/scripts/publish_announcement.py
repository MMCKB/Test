from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="发布一次性 ClassWidgets 集控公告")
    parser.add_argument("--title", required=True)
    parser.add_argument("--message", required=True)
    parser.add_argument("--duration", type=int, default=8000)
    args = parser.parse_args()

    title = args.title.strip()
    message = args.message.strip()
    if not title or not message:
        raise SystemExit("公告标题和内容不能为空")
    if len(title) > 80 or len(message) > 500:
        raise SystemExit("公告标题或内容超过集控客户端限制")

    duration = max(1000, min(args.duration, 60000))
    run_id = os.environ.get("GITHUB_RUN_ID", datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S"))
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=1)

    manifest_path = Path("manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["policyVersion"] = f"announcement-{run_id}"
    manifest["commands"] = [
        {
            "id": f"announcement-{run_id}",
            "type": "announcement",
            "title": title,
            "message": message,
            "duration": duration,
            "expiresAt": expires_at.isoformat().replace("+00:00", "Z"),
        }
    ]
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Published announcement-{run_id}; expires at {manifest['commands'][0]['expiresAt']}")


if __name__ == "__main__":
    main()
