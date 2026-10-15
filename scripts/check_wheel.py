"""Check wheel contents and import its resources outside the source checkout.

Usage: python scripts/check_wheel.py dist/*.whl
Dependencies must already be installed (as in the CI test environment).
"""

from __future__ import annotations

import argparse
import glob
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

SMOKE = """
import socket
import sys
from pathlib import Path

def refuse_network(*args, **kwargs):
    raise AssertionError("wheel smoke check must not use the network")

socket.socket.connect = refuse_network
socket.create_connection = refuse_network
installed = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(installed))
from telegram_ads_mcp import guide
from telegram_ads_mcp.server import guide_resource, mcp, playbook_resource
import tg_ads_mcp

assert Path(guide.__file__).resolve().is_relative_to(installed)
assert guide.PLAYBOOK_PATH == installed / "telegram_ads_mcp" / "PLAYBOOK.md"
expected = guide.PLAYBOOK_PATH.read_text(encoding="utf-8")
assert "## Auth" in expected and "## Write gate" in expected
assert playbook_resource() == expected
for name in guide.TOPICS:
    body = guide.topic(name)
    assert body and body.startswith("## "), name
    assert guide_resource(name) == body, name
assert mcp.name == "telegram-ads-mcp"
print("installed playbook and all topic guides resolve")
"""


def check_wheel(path: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="telegram-ads-wheel-") as directory:
        installed = Path(directory)
        with zipfile.ZipFile(path) as wheel:
            names = set(wheel.namelist())
            assert "telegram_ads_mcp/PLAYBOOK.md" in names, "wheel is missing the client playbook"
            assert "telegram_ads_mcp/AGENTS.md" not in names, "wheel contains auto-loaded dev instructions"
            for schema in ("campaign-brief", "review-artifact", "stats-dump"):
                assert f"telegram_ads_mcp/schemas/{schema}.schema.json" in names, schema
            wheel.extractall(installed)
        env = {key: value for key, value in os.environ.items() if not key.startswith("STEL_")}
        env["TG_ADS_DISABLE_UPDATE_CHECK"] = "1"
        env["TG_ADS_ENV_FILE"] = str(installed / "empty.env")
        (installed / "empty.env").write_text("", encoding="utf-8")
        subprocess.run(
            [sys.executable, "-I", "-c", SMOKE, str(installed)],
            cwd=installed,
            env=env,
            check=True,
            timeout=60,
        )
    print(f"ok: {path.name}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheels", nargs="+")
    args = parser.parse_args()
    paths: set[Path] = set()
    for pattern in args.wheels:
        matches = glob.glob(pattern)
        if not matches:
            parser.error(f"no wheel matches {pattern!r}")
        paths.update(Path(path).resolve() for path in matches)
    for path in sorted(paths):
        check_wheel(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
