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
    monkeypatch.setattr(app_storage, "IS_WINDOWS", True)
    monkeypatch.setattr(app_storage, "verify_private_directory", lambda path: checked.append(path))
    monkeypatch.setattr(app_storage, "private_directory", lambda _: pytest.fail("must not tighten saved root"))
    assert app_storage.prepare_data_directory(directory) == directory
    assert checked == [directory]
    assert saved.read_bytes() == b"retained competition"


def test_shared_nonempty_windows_data_fails_without_mutation(tmp_path, monkeypatch):
    directory = tmp_path / "shared"
    directory.mkdir()
    document = directory / "unrelated.txt"
    document.write_bytes(b"unchanged")
    monkeypatch.setattr(app_storage, "IS_WINDOWS", True)

    def untrusted(_path):
        raise PermissionError("not private")

    monkeypatch.setattr(app_storage, "verify_private_directory", untrusted)
    with pytest.raises(PermissionError, match="not private"):
        app_storage.prepare_data_directory(directory)
    assert list(directory.iterdir()) == [document]
    assert document.read_bytes() == b"unchanged"


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
