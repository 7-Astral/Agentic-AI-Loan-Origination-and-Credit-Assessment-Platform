import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "security" / "reports"

DEFAULT_PROBES = [
    "promptinject",
    "dan",
    "encoding",
    "latentinjection",
    "goodside",
    "sysprompt_extraction",
    "smuggling",
    "web_injection",
    "grandma",
    "misleading",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a garak scan against the loan advisor agent.")
    parser.add_argument("--target", choices=["advisor", "advisor_unguarded"], default="advisor")
    parser.add_argument("--probes", default=",".join(DEFAULT_PROBES))
    parser.add_argument("--generations", type=int, default=1)
    args = parser.parse_args()

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    config = {"reporting": {"report_dir": str(REPORT_DIR)}, "system": {"parallel_attempts": False}}
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
        json.dump(config, handle)
        config_path = handle.name

    command = [
        sys.executable, "-m", "garak",
        "--config", config_path,
        "--target_type", "function",
        "--target_name", f"security.garak_target#{args.target}",
        "--probes", args.probes,
        "--generations", str(args.generations),
        "--report_prefix", f"loan-{args.target}",
    ]
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(filter(None, [str(ROOT), os.environ.get("PYTHONPATH")]))}
    try:
        return subprocess.call(command, cwd=ROOT, env=env)
    finally:
        os.unlink(config_path)


if __name__ == "__main__":
    raise SystemExit(main())
