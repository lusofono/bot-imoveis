"""02/10: the backups — the data folder zipped once a day (at the first read) into a folder the owner chose; never the
keys or the lock and temporary files; nothing deleted, only added; Google Drive for desktop's folder offered."""
import zipfile
from datetime import datetime, timedelta
import pytest
from test_properties import lead, read, service  # noqa: F401 (service is a fixture)


def test_a_backup_has_the_data_but_never_the_keys_and_none_is_ever_deleted(service, tmp_path_factory):
    copies = tmp_path_factory.mktemp("copias")
    with pytest.raises(ValueError, match="caminho completo"):
        service.set_backup_folder("relativa/pasta")
    with pytest.raises(ValueError, match="dentro da pasta de dados"):
        service.set_backup_folder(str(service.folder / "properties"))
    (service.folder / "secrets").mkdir()
    (service.folder / "secrets" / "openai_api_key").write_text("sk-nunca")
    (service.folder / ".queue.lock").write_text("")
    assert service.set_backup_folder(str(copies))["folder"] == str(copies)
    result = service.backup()
    [made] = list(copies.glob("ARIA-copia-*.zip"))
    names = zipfile.ZipFile(made).namelist()
    assert "data/config.json" in names and "data/voice.json" in names
    assert not any("secrets" in name or "/." in name for name in names)
    assert result["last"]["file"] == made.name and result["count"] == 1
    start = datetime(2026, 1, 1)
    for day in range(20):
        service.backup(start + timedelta(days=day))
    assert len(list(copies.glob("ARIA-copia-*.zip"))) == 21  # only added, never deleted


def test_one_backup_a_day_at_the_read_and_none_without_a_folder(service, tmp_path_factory):
    read(service, [lead("1")])  # no folder: nothing
    copies = tmp_path_factory.mktemp("copias")
    service.set_backup_folder(str(copies))
    read(service, [lead("2")])
    read(service, [lead("3")])  # the same day: still one
    assert len(list(copies.glob("ARIA-copia-*.zip"))) == 1


def test_google_drive_for_desktop_is_offered_and_its_folder_made(service, tmp_path_factory, monkeypatch):
    from pathlib import Path
    home = tmp_path_factory.mktemp("home")
    drive = home / "Library" / "CloudStorage" / "GoogleDrive-dono@example.com" / "O meu disco"
    drive.mkdir(parents=True)
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))
    [found] = service.backup_settings()["drives"]
    assert found == {"account": "dono@example.com", "path": str(drive / "ARIA-copias")}
    assert service.set_backup_folder(found["path"], create=True)["folder"] == found["path"]
    assert (drive / "ARIA-copias").is_dir()


def test_the_macs_folder_chooser_gives_the_folder_or_says_none_was_chosen(service, tmp_path_factory):
    import subprocess
    from unittest.mock import patch
    chosen = tmp_path_factory.mktemp("escolhida")
    done = subprocess.CompletedProcess([], 0, stdout=f"{chosen}/\n", stderr="")
    with patch("backend.service.sys.platform", "darwin"), patch("backend.service.subprocess.run", return_value=done):
        assert service.set_backup_folder(service.choose_folder())["folder"] == str(chosen)
    cancelled = subprocess.CompletedProcess([], 1, stdout="", stderr="User canceled.")
    with patch("backend.service.sys.platform", "darwin"), patch("backend.service.subprocess.run", return_value=cancelled):
        with pytest.raises(ValueError, match="Nenhuma pasta"):
            service.choose_folder()
