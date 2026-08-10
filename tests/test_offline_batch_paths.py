"""Static checks for paths used by the Windows offline installer."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "offline" / "INSTALL_OFFLINE.bat"


def test_installer_points_pip_to_bundled_wheelhouse() -> None:
    script = INSTALLER.read_text(encoding="utf-8")

    assert '--find-links "%BUNDLE_ROOT%\\wheelhouse"' in script
    assert '--find-links "%BUNDLE_ROOT%wheelhouse"' not in script
