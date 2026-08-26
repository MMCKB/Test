from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path


POWER_ACTIONS = {"restart", "shutdown", "hibernate", "sleep"}
MIN_DELAY_SECONDS = 10
MAX_DELAY_SECONDS = 300


def main() -> None:
    parser = argparse.ArgumentParser(description="发布一次性 ClassWidgets 集控电源命令")
    parser.add_argument("--action", required=True, choices=sorted(POWER_ACTIONS))
    parser.add_argument("--delay-seconds", type=int, default=30)
    args = parser.parse_args()

    if not MIN_DELAY_SECONDS <= args.delay_seconds <= MAX_DELAY_SECONDS:
        raise SystemExit(
            f"电源命令倒计时必须在 {MIN_DELAY_SECONDS} 至 {MAX_DELAY_SECONDS} 秒之间"
        )

    run_id = os.environ.get("GITHUB_RUN_ID", datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S"))
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=10)

    manifest_path = Path("manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["policyVersion"] = f"power-{run_id}"
    manifest["commands"] = [
        {
            "id": f"power-{run_id}",
            "type": "power",
            "action": args.action,
            "delaySeconds": args.delay_seconds,
            "expiresAt": expires_at.isoformat().replace("+00:00", "Z"),
        }
    ]
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"Published power-{run_id}: {args.action}; "
        f"delay {args.delay_seconds}s; expires at {manifest['commands'][0]['expiresAt']}"
    )


if __name__ == "__main__":
    main()
