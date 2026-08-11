"""Static checks for paths used by the Windows offline installer."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "offline" / "INSTALL_OFFLINE.bat"
BUILDER = ROOT / "offline" / "build_offline_bundle.ps1"


def test_installer_points_pip_to_bundled_wheelhouse() -> None:
    script = INSTALLER.read_text(encoding="utf-8")

    assert '--find-links "%BUNDLE_ROOT%\\wheelhouse"' in script
    assert '--find-links "%BUNDLE_ROOT%wheelhouse"' not in script


def test_bundle_manifest_excludes_mutable_gui_settings() -> None:
    script = BUILDER.read_text(encoding="utf-8")

    assert "$mutableRelativePaths = @('app/config/gui_config.ini')" in script
    assert "if ($relative -in $mutableRelativePaths) { continue }" in script


def test_dirty_bundle_filters_files_deleted_from_the_worktree() -> None:
    script = BUILDER.read_text(encoding="utf-8")

    assert "Test-Path -LiteralPath $worktreePath -PathType Leaf" in script


def test_dirty_bundle_does_not_copy_untracked_generated_outputs() -> None:
    script = BUILDER.read_text(encoding="utf-8")

    assert "ls-files --cached --others" not in script
    assert "git -c core.quotepath=false -C $repoRoot ls-files" in script
