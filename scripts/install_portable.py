"""Install, select, or roll back immutable Linux STRATH release profiles.

This standard-library bootstrap runs outside a checkout. A private release bundle
contains SHA256-pinned wheels for separate V2/app and V3 environments plus the
operator's candidate model. No profile, competition, key, or model is overwritten.
"""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


def read_json(path):
    if path.stat().st_size > 1_000_000:
        raise ValueError("installation manifest exceeds 1 MB")
    return json.loads(path.read_text())


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(value, stream, indent=2, sort_keys=True)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextlib.contextmanager
def installation_lock(home):
    home.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (home / ".profile.lock").open("a+b") as stream:
        os.chmod(stream.name, 0o600)
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError("close the running STRATH application before switching profiles") from exc
        yield


def identifier(value):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,100}", value):
        raise ValueError("invalid release profile identifier")
    return value


def profile(home, release):
    return read_json(home / "profiles" / identifier(release) / "profile.json")


def recovery_archive(home, backup, workbook):
    backup = backup.resolve(strict=True)
    if backup.stat().st_dev == home.stat().st_dev:
        raise ValueError("rollback archive must be on an independent filesystem")
    destination = backup / (
        "profile-switch-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex + ".tar.gz"
    )
    files = {}
    for path in home.rglob("*"):
        if (
            path.is_file()
            and not path.is_symlink()
            and (
                path.name in {"profile.json", "active.json"}
                or "data" in path.relative_to(home).parts
                or "authority" in path.relative_to(home).parts
            )
        ):
            files["installation/" + path.relative_to(home).as_posix()] = path
    files["operator-workbook.xlsx"] = workbook
    # Adopted profiles can keep their original paths. Their authority and saved
    # competitions must be preserved just as completely as new managed profiles.
    for descriptor in sorted(home.glob("profiles/*/profile.json")):
        saved = read_json(descriptor)
        prefix = "retained-profiles/" + identifier(saved["release_id"])
        for key in ("data_dir", "runtime_root"):
            root = Path(saved[key])
            if root.exists():
                for path in root.rglob("*"):
                    if path.is_symlink():
                        raise ValueError("competition recovery data must not contain symlinks")
                    if path.is_file():
                        files[prefix + "/" + key + "/" + path.relative_to(root).as_posix()] = path
        files[prefix + "/operator-workbook.xlsx"] = Path(saved["workbook"])
    expected = {name: sha(path) for name, path in files.items()}
    with tarfile.open(destination, "x:gz") as archive:
        for name, path in files.items():
            archive.add(path, arcname=name, recursive=False)
    with destination.open("rb") as stream:
        os.fsync(stream.fileno())
    with tarfile.open(destination, "r:gz") as archive:
        actual = {
            item.name: hashlib.sha256(archive.extractfile(item).read()).hexdigest()
            for item in archive.getmembers()
            if item.isfile()
        }
    if actual != expected or any(sha(path) != expected[name] for name, path in files.items()):
        raise ValueError("independent rollback archive failed read-back verification")
    atomic_json(
        destination.with_suffix(".verified.json"),
        {
            "archive_sha256": sha(destination),
            "files": expected,
            "reason": "preserve keys, saved competitions, outboxes and workbook before profile selection",
        },
    )
    return str(destination)


def activate(home, release):
    selected = profile(home, release)
    if selected["state"] != "verified":
        raise ValueError("installation profile has not passed its installed checks")
    for key in ("app_python", "runtime_python", "workbook", "backup_dir"):
        if not Path(selected[key]).exists():
            raise ValueError(f"profile prerequisite unavailable: {key}")
    previous = read_json(home / "active.json") if (home / "active.json").exists() else None
    backup = recovery_archive(home, Path(selected["backup_dir"]), Path(selected["workbook"]))
    atomic_json(
        home / "active.json",
        {
            "release_id": release,
            "previous": None if previous is None else previous["release_id"],
            "recovery_archive": backup,
        },
    )
    return selected


def verify_bundle(bundle):
    manifest = read_json(bundle / "release.json")
    if manifest["schema_version"] != "strath-portable-release-v1" or manifest["python"] != "3.13":
        raise ValueError("unsupported portable release")
    identifier(manifest["release_id"])
    if not manifest["files"] or len(manifest["files"]) > 300:
        raise ValueError("invalid release file count")
    for name, item in manifest["files"].items():
        relative = Path(name)
        if relative.is_absolute() or ".." in relative.parts or not relative.parts:
            raise ValueError("release path escapes its bundle")
        path = bundle / relative
        if any(parent.is_symlink() for parent in (path, *path.parents) if parent != bundle.parent):
            raise ValueError("release paths must not contain symlinks")
        path = path.resolve(strict=True)
        if not path.is_relative_to(bundle) or not path.is_file():
            raise ValueError("release path escapes its bundle")
        if (
            not isinstance(item["bytes"], int)
            or isinstance(item["bytes"], bool)
            or item["bytes"] < 0
            or not isinstance(item["sha256"], str)
            or not re.fullmatch(r"[0-9a-f]{64}", item["sha256"])
            or not isinstance(item["roles"], list)
            or not set(item["roles"]) <= {"app", "runtime", "model", "formula", "bootstrap"}
        ):
            raise ValueError("invalid release file identity")
        if path.stat().st_size != item["bytes"] or sha(path) != item["sha256"]:
            raise ValueError(f"release file checksum mismatch: {name}")
    for role in ("app", "runtime"):
        wheels = [name for name, item in manifest["files"].items() if role in item["roles"]]
        if not wheels or any(not name.endswith(".whl") for name in wheels):
            raise ValueError("release environment requires a complete pinned wheel set")
    return manifest


def install(home, bundle, workbook, backup, uv):
    bundle = bundle.resolve(strict=True)
    manifest = verify_bundle(bundle)
    release = identifier(manifest["release_id"])
    workbook = workbook.resolve(strict=True)
    backup = backup.resolve(strict=True)
    if backup.stat().st_dev == home.stat().st_dev:
        raise ValueError("installation requires an independent recovery filesystem")
    root = home / "profiles" / release
    root.mkdir(parents=True, exist_ok=False, mode=0o700)
    try:
        for role in ("app", "runtime"):
            env = root / role
            subprocess.run([uv, "venv", "--python", manifest["python"], str(env)], check=True)
            wheels = [str(bundle / name) for name, item in manifest["files"].items() if role in item["roles"]]
            subprocess.run(
                [uv, "pip", "install", "--python", str(env / "bin/python"), "--no-deps", "--no-index", *wheels],
                check=True,
            )
        model = root / "model"
        model.mkdir(mode=0o700)
        for name, item in manifest["files"].items():
            if "model" in item["roles"]:
                source = bundle / name
                target = model / source.relative_to(bundle / manifest["model_directory"])
                target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                shutil.copyfile(source, target)
                os.chmod(target, 0o600)
            if "formula" in item["roles"]:
                if name != manifest.get("formula_file"):
                    raise ValueError("release Formula identity is ambiguous")
                shutil.copyfile(bundle / name, root / "formula_manifest.json")
                os.chmod(root / "formula_manifest.json", 0o600)
        python = root / "runtime/bin/python"
        code = "from strathmark.v3.runtime_identity import implementation_digest; print(implementation_digest())"
        if (
            subprocess.check_output([str(python), "-I", "-c", code], text=True).strip()
            != manifest["runtime_implementation_digest"]
        ):
            raise ValueError("installed runtime differs from the release implementation")
        code = "import sys,catboost;from strathmark.v3.factory.ml_artifacts import load_ml_bundle; print(load_ml_bundle(sys.argv[1],installed_catboost_version=catboost.__version__,installed_python_abi='cp313').digest)"
        if (
            subprocess.check_output([str(python), "-I", "-c", code, str(model)], text=True).strip()
            != manifest["model_digest"]
        ):
            raise ValueError("installed model differs from the release bundle")
        if manifest.get("formula_digest"):
            code = "import sys;from strathmark.v3.linux_forecasts import load_formula_manifest;print(load_formula_manifest(__import__('pathlib').Path(sys.argv[1])).digest)"
            if (
                subprocess.check_output([str(python), "-I", "-c", code, str(model)], text=True).strip()
                != manifest["formula_digest"]
            ):
                raise ValueError("installed Formula differs from the release candidate")
        for role, expected in (("app", manifest.get("app_version")), ("runtime", manifest.get("runtime_version"))):
            if expected:
                module = "woodchopping" if role == "app" else "strathmark"
                observed = subprocess.check_output(
                    [str(root / role / "bin/python"), "-I", "-c", f"import {module};print({module}.__version__)"],
                    text=True,
                ).strip()
                if observed != expected:
                    raise ValueError("installed package version differs from its release")
        if manifest.get("v2_source_digest"):
            code = "import strathmark,pathlib,hashlib,json;root=pathlib.Path(strathmark.__file__).parent;content={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*.py')};print(hashlib.sha256(json.dumps(content,sort_keys=True,separators=(',',':')).encode()).hexdigest())"
            observed = subprocess.check_output([str(root / "app/bin/python"), "-I", "-c", code], text=True).strip()
            if observed != manifest["v2_source_digest"]:
                raise ValueError("installed V2 differs from its frozen source")
        subprocess.run(
            [str(root / "app/bin/python"), "-I", "-m", "strathex_cli", "--help"],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        subprocess.run(
            [
                str(python),
                "-I",
                "-m",
                "strathmark.v3.linux_lifecycle",
                "init",
                "--runtime-root",
                str(root / "authority"),
                "--ml-bundle",
                str(model),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        data = {
            "schema_version": "strath-portable-profile-v1",
            "release_id": release,
            "state": "verified",
            "app_python": str(root / "app/bin/python"),
            "runtime_python": str(python),
            "model": str(model),
            "workbook": str(workbook),
            "backup_dir": str(backup),
            "data_dir": str(root / "data"),
            "runtime_root": str(root / "authority"),
            "release_manifest": manifest,
        }
        atomic_json(root / "profile.json", data)
        activate(home, release)
        return data
    except Exception:
        atomic_json(
            root / "installation-failed.json",
            {"release_id": release, "state": "failed", "active_profile_changed": False},
        )
        raise


def launch(home, release, arguments, runtime=False):
    selected = profile(home, release or read_json(home / "active.json")["release_id"])
    if selected["state"] != "verified":
        raise ValueError("profile is not verified")
    if not Path(selected["backup_dir"]).is_dir():
        raise ValueError("connect the independent recovery drive before starting STRATH")
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("STRATHMARK_", "STRATHEX_", "PYTHONPATH", "PYTHONHOME"))
    }
    if runtime:
        command = [
            selected["runtime_python"],
            "-I",
            "-m",
            "strathmark.v3.linux_lifecycle",
            *arguments,
            "--runtime-root",
            selected["runtime_root"],
            "--ml-bundle",
            selected["model"],
        ]
    else:
        command = [
            selected["app_python"],
            "-I",
            "-m",
            "strathex_cli",
            "--workbook",
            selected["workbook"],
            "--data-dir",
            selected["data_dir"],
            "--local-v3-python",
            selected["runtime_python"],
            "--local-v3-ml-bundle",
            selected["model"],
            "--local-v3-runtime-root",
            selected["runtime_root"],
            "--local-v3-backup-dir",
            selected["backup_dir"],
            *arguments,
        ]
    return subprocess.call(command, env=environment)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", type=Path, default=Path.home() / ".local/share/strath/installations")
    sub = parser.add_subparsers(dest="operation", required=True)
    setup = sub.add_parser("install")
    setup.add_argument("--bundle", type=Path, required=True)
    setup.add_argument("--workbook", type=Path, required=True)
    setup.add_argument("--backup-dir", type=Path, required=True)
    setup.add_argument("--uv", default=shutil.which("uv"))
    choice = sub.add_parser("activate")
    choice.add_argument("release_id")
    sub.add_parser("list")
    sub.add_parser("rollback")
    for name in ("launch", "runtime"):
        command = sub.add_parser(name)
        command.add_argument("--profile")
        command.add_argument("arguments", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    try:
        home = args.home.resolve()
        with installation_lock(home):
            if args.operation == "install":
                if not args.uv:
                    raise ValueError("uv is required to provision Python 3.13 environments")
                print(json.dumps(install(home, args.bundle, args.workbook, args.backup_dir, args.uv), indent=2))
            elif args.operation == "activate":
                print(json.dumps(activate(home, args.release_id), indent=2))
            elif args.operation == "list":
                print(
                    json.dumps(
                        {
                            "active": read_json(home / "active.json") if (home / "active.json").exists() else None,
                            "profiles": [read_json(path) for path in sorted(home.glob("profiles/*/profile.json"))],
                        },
                        indent=2,
                    )
                )
            elif args.operation == "rollback":
                previous = read_json(home / "active.json").get("previous")
                if previous is None:
                    raise ValueError("no previous verified profile is recorded")
                print(json.dumps(activate(home, previous), indent=2))
            else:
                arguments = args.arguments[1:] if args.arguments[:1] == ["--"] else args.arguments
                return launch(home, args.profile, arguments, runtime=args.operation == "runtime")
        return 0
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
