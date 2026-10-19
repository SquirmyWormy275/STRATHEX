"""Exercise an installed STRATHEX launcher without legacy workbook startup."""

import argparse
import json
import os
import subprocess
import tempfile
import venv
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--managed-python", type=Path, required=True)
    args = parser.parse_args()
    wheel = args.wheel.resolve(strict=True)
    producer = args.managed_python.absolute()
    if not producer.is_file():
        raise ValueError("Explicit installed managed interpreter required")
    with tempfile.TemporaryDirectory(prefix="strathex-managed-client-") as temporary:
        root = Path(temporary)
        environment = root / "consumer"
        venv.EnvBuilder(with_pip=True).create(environment)
        python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        subprocess.run([str(python), "-m", "pip", "install", str(wheel)], check=True, timeout=300)
        child_env = {
            key: value for key, value in os.environ.items() if not key.startswith(("STRATHMARK_", "STRATHEX_"))
        }
        child_env.update(
            STRATHMARK_TEST_DB="1",
            STRATHMARK_DB_PATH=str(root / "v2.db"),
            STRATHMARK_V3_DB_PATH=str(root / "v3.db"),
            PYTHONUTF8="1",
        )

        def command(*arguments, success=True):
            result = subprocess.run(
                [
                    str(python),
                    "-I",
                    "-m",
                    "strathex_cli",
                    "--managed-cli-python",
                    str(producer),
                    "--managed",
                    *arguments,
                ],
                cwd=root,
                env=child_env,
                capture_output=True,
                text=True,
                timeout=60,
            )
            if success and result.returncode:
                raise AssertionError(result.stdout + result.stderr)
            return result

        capabilities = json.loads(command("capabilities", "--json").stdout)
        assert capabilities["official_use"] is False
        config = root / "config.json"
        command("example", "--output", str(config))
        supplied = json.loads(config.read_text())
        event_id = supplied["event_id"]
        database = root / "managed.sqlite3"
        created = json.loads(
            command(
                "event",
                "create",
                "--database",
                str(database),
                "--input",
                str(config),
                "--request-id",
                "client-create",
                "--json",
            ).stdout
        )
        assert created["config"]["engine"] == "v2" and created["revision"] == 1
        reopened = json.loads(
            command("event", "status", "--database", str(database), "--event-id", event_id, "--json").stdout
        )
        assert reopened == created
        denied = command(
            "event",
            "status",
            "--database",
            str(database),
            "--event-id",
            event_id,
            "--show",
            "synthetic:wrong",
            "--json",
            success=False,
        )
        assert denied.returncode != 0 and "forbidden_show" in denied.stdout + denied.stderr
        assert not list(root.glob("*.xlsx")) and not (root / "saves").exists()
        print(
            json.dumps(
                {
                    "status": "PASS",
                    "consumer": "installed STRATHEX 7.4.5",
                    "producer_contract": capabilities["schema_version"],
                    "checks": ["supplied configuration", "persistent resume", "scope refusal", "no workbook startup"],
                    "official_use": False,
                }
            )
        )


if __name__ == "__main__":
    main()
