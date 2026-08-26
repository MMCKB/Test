from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path


POWER_ACTIONS = {"restart", "shutdown", "hibernate", "sleep"}


def main() -> None:
    parser = argparse.ArgumentParser(description="发布一次性 ClassWidgets 集控电源命令")
    parser.add_argument("--action", required=True, choices=sorted(POWER_ACTIONS))
    args = parser.parse_args()

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
            "expiresAt": expires_at.isoformat().replace("+00:00", "Z"),
        }
    ]
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"Published power-{run_id}: {args.action}; "
        f"expires at {manifest['commands'][0]['expiresAt']}"
    )


if __name__ == "__main__":
    main()
