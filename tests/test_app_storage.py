import os
from pathlib import Path

import pytest

from woodchopping import app_storage


def test_new_data_directory_is_explicitly_provisioned(tmp_path):
    directory = app_storage.prepare_data_directory(tmp_path / "new-app-data")
    assert directory.is_dir()
    assert list(directory.iterdir()) == []


def test_existing_nonempty_data_is_verified_without_acl_changes(tmp_path, monkeypatch):
    directory = tmp_path / "saved-data"
    directory.mkdir()
    saved = directory / "competition.json"
    saved.write_bytes(b"retained competition")
    checked = []
    monkeypatch.setattr(app_storage, "verify_private_directory", lambda path: checked.append(path))
    monkeypatch.setattr(app_storage, "private_directory", lambda _: pytest.fail("must not tighten saved root"))
    assert app_storage.prepare_data_directory(directory) == directory
    assert checked == [directory]
    assert saved.read_bytes() == b"retained competition"


def test_shared_nonempty_data_fails_without_mutation(tmp_path, monkeypatch):
    directory = tmp_path / "shared"
    directory.mkdir()
    document = directory / "unrelated.txt"
    document.write_bytes(b"unchanged")

    def untrusted(_path):
        raise PermissionError("not private")

    monkeypatch.setattr(app_storage, "verify_private_directory", untrusted)
    with pytest.raises(PermissionError, match="not private"):
        app_storage.prepare_data_directory(directory)
    assert list(directory.iterdir()) == [document]
    assert document.read_bytes() == b"unchanged"


@pytest.mark.skipif(os.name != "posix", reason="POSIX mode regression")
def test_existing_peer_readable_data_is_rejected_without_chmod(tmp_path):
    directory = tmp_path / "saved-data"
    directory.mkdir(mode=0o755)
    directory.chmod(0o755)
    saved = directory / "competition.json"
    saved.write_bytes(b"retained competition")
    before = directory.stat().st_mode
    with pytest.raises(PermissionError, match="private"):
        app_storage.prepare_data_directory(directory)
    assert directory.stat().st_mode == before
    assert saved.read_bytes() == b"retained competition"
    directory.chmod(0o700)
    assert app_storage.prepare_data_directory(directory) == directory


@pytest.mark.skipif(os.name != "posix", reason="POSIX mode regression")
@pytest.mark.parametrize("store_name", ["selection", "commands"])
def test_direct_authority_stores_reject_shared_parents_and_create_private_files(tmp_path, store_name):
    from woodchopping.ui.prediction_context import PredictionAuthorityStore
    from woodchopping.v3_authority_store import V3CommandStore

    store = PredictionAuthorityStore if store_name == "selection" else V3CommandStore
    parent = tmp_path / "shared"
    parent.mkdir(mode=0o777)
    parent.chmod(0o777)
    path = parent / "authority.db"
    with pytest.raises(PermissionError):
        store(path)
    assert not path.exists()
    parent.chmod(0o700)
    previous = os.umask(0)
    try:
        store(path)
    finally:
        os.umask(previous)
    assert path.stat().st_mode & 0o777 == 0o600


def test_home_checkout_and_workbook_directories_are_not_repermissioned(tmp_path):
    with pytest.raises(ValueError, match="dedicated"):
        app_storage.prepare_data_directory(Path.home())
    (tmp_path / ".git").mkdir()
    with pytest.raises(ValueError, match="checkout"):
        app_storage.prepare_data_directory(tmp_path)
    workbook_root = tmp_path / "workbooks"
    workbook_root.mkdir()
    with pytest.raises(ValueError, match="workbook"):
        app_storage.prepare_data_directory(workbook_root, workbook=workbook_root / "competition.xlsx")
