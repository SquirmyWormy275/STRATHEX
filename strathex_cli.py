"""Portable launcher that selects operator paths before application imports."""

from __future__ import annotations

import argparse
import os
import runpy
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Run STRATHEX with a selected workbook and data directory.")
    parser.add_argument(
        "--managed-workspace-url",
        help="Optional shared STRATHMARK workspace origin; sign in there with a scoped operator account",
    )
    parser.add_argument("--managed-event-id", help="Existing persistent shared event identity")
    parser.add_argument(
        "--managed-cli-python", type=Path, help="Explicit separate interpreter for shared STRATHMARK operations"
    )
    parser.add_argument(
        "--managed", nargs=argparse.REMAINDER, help="Pass remaining arguments to the standalone STRATHMARK CLI"
    )
    parser.add_argument("--workbook", type=Path, help="Existing workbook with Competitor, Wood, and Results sheets")
    parser.add_argument("--data-dir", type=Path, help="Directory for saves, authority, commands, and ResultStore")
    parser.add_argument(
        "--local-v3-python",
        type=Path,
        help="Separate Python 3.13 environment with installed STRATHMARK V3",
    )
    parser.add_argument(
        "--local-v3-ml-bundle",
        type=Path,
        help="Verified, trained V3 ML bundle",
    )
    parser.add_argument(
        "--local-v3-runtime-root",
        type=Path,
        help="Persistent Linux competition authority; enables approval, issue, settlement and later rounds",
    )
    parser.add_argument(
        "--local-v3-backup-dir",
        type=Path,
        help="Existing independent disk directory for verified Linux authority and workbook recovery copies",
    )
    parser.add_argument(
        "--correct-v3-results",
        type=Path,
        help="Saved competition JSON to append an official result correction instead of starting the menu",
    )
    parser.add_argument(
        "--local-v3-backup-encryption-policy",
        type=Path,
        help="Pinned local GPG backup policy for the separate Linux V3 runtime",
    )
    args = parser.parse_args()
    if args.managed_workspace_url is not None:
        import webbrowser

        from woodchopping.managed_launcher import workspace_url

        try:
            target = workspace_url(args.managed_workspace_url, args.managed_event_id)
        except ValueError as exc:
            parser.error(str(exc))
        if not webbrowser.open(target):
            parser.error("The browser could not open the configured workspace origin.")
        print(
            "Shared workspace opened. Sign in with your event-scoped operator account; use deliberate CLI/GUI editor handover."
        )
        return
    if args.managed is not None:
        if args.managed_cli_python is None:
            parser.error("--managed requires --managed-cli-python; no runtime is selected automatically")
        from woodchopping.managed_launcher import run_cli

        raise SystemExit(run_cli(args.managed_cli_python, args.managed))
    if args.local_v3_backup_encryption_policy is not None:
        if args.local_v3_backup_dir is None or not args.local_v3_backup_encryption_policy.is_file():
            parser.error("backup encryption requires an existing policy and recovery directory")
        os.environ["STRATHEX_V3_LOCAL_BACKUP_ENCRYPTION_POLICY"] = str(args.local_v3_backup_encryption_policy.resolve())
    if args.correct_v3_results is not None:
        args.correct_v3_results = args.correct_v3_results.expanduser().resolve()
    if args.local_v3_runtime_root is not None and os.environ.get("STRATHEX_TEST_DB") != "1":
        if args.local_v3_backup_dir is None:
            parser.error("Linux operator competitions require --local-v3-backup-dir on an independent disk")
        if (
            args.workbook is not None
            and args.local_v3_backup_dir.exists()
            and args.workbook.exists()
            and args.local_v3_backup_dir.stat().st_dev == args.workbook.stat().st_dev
        ):
            parser.error("Linux recovery directory must be on a different filesystem from the live workbook")
    if args.local_v3_backup_dir is not None:
        if args.local_v3_runtime_root is None or not args.local_v3_backup_dir.is_dir():
            parser.error("--local-v3-backup-dir requires a Linux runtime and an existing recovery directory")
        os.environ["STRATHEX_V3_LOCAL_BACKUP_DIR"] = str(args.local_v3_backup_dir.resolve())
        os.environ["STRATHEX_WORKBOOK_BACKUP_DIR"] = str(args.local_v3_backup_dir.resolve())
    if args.local_v3_runtime_root is not None and args.local_v3_python is None:
        parser.error("--local-v3-runtime-root requires the separate V3 Python and ML bundle")
    if (args.local_v3_python is None) != (args.local_v3_ml_bundle is None):
        parser.error("--local-v3-python and --local-v3-ml-bundle must be supplied together")
    if args.local_v3_python is not None:
        if args.workbook is None or args.data_dir is None:
            parser.error("local V3 requires an explicit --workbook and --data-dir")
        if not args.local_v3_python.expanduser().is_file() or (
            not args.local_v3_ml_bundle.expanduser().is_dir() and args.correct_v3_results is None
        ):
            parser.error("local V3 Python or ML bundle does not exist")
        os.environ["STRATHEX_V3_LOCAL_PYTHON"] = str(args.local_v3_python.expanduser().absolute())
        os.environ["STRATHEX_V3_LOCAL_ML_BUNDLE"] = str(args.local_v3_ml_bundle.expanduser().resolve())
        os.environ["STRATHEX_V3_LOCAL_SNAPSHOTS"] = str(args.data_dir.expanduser().resolve() / "v3-preview-snapshots")
        if args.local_v3_runtime_root is not None:
            os.environ["STRATHEX_V3_LOCAL_RUNTIME_ROOT"] = str(args.local_v3_runtime_root.expanduser().absolute())
    if args.workbook is not None:
        workbook = args.workbook.expanduser().resolve()
        if not workbook.is_file():
            parser.error(f"workbook does not exist: {workbook}")
        os.environ["STRATHEX_WORKBOOK"] = str(workbook)
    if args.data_dir is not None:
        from woodchopping.app_storage import prepare_data_directory

        try:
            directory = prepare_data_directory(args.data_dir, workbook=args.workbook)
        except (OSError, ValueError) as exc:
            parser.error(str(exc))
        os.environ.setdefault("STRATHMARK_DB_PATH", str(directory / "results.db"))
        os.environ.setdefault("STRATHEX_PREDICTION_AUTHORITY_DB", str(directory / "prediction_authority.db"))
        os.environ.setdefault("STRATHEX_V3_COMMAND_DB", str(directory / "v3_commands.db"))
        os.chdir(directory)
    if args.correct_v3_results is not None:
        from woodchopping.ui.linux_results import correct_saved_results

        correct_saved_results(args.correct_v3_results.expanduser().resolve())
        return
    runpy.run_module("MainProgramV5_2", run_name="__main__")


if __name__ == "__main__":
    main()
