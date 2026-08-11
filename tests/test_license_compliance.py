import csv
import io
import json
import struct
import zipfile
from pathlib import Path

import pytest

from offline import license_compliance as compliance


def _wheel(path: Path, name="Example", version="1.0", *, license_file=True, extra=None):
    dist = name.replace("-", "_")
    metadata = (
        "Metadata-Version: 2.4\n"
        f"Name: {name}\n"
        f"Version: {version}\n"
        "License-Expression: MIT\n"
        "Project-URL: Source, https://example.invalid/source\n\n"
    ).encode()
    members = {
        f"{dist}-{version}.dist-info/METADATA": metadata,
        f"{dist}-{version}.dist-info/WHEEL": b"Wheel-Version: 1.0\nTag: py3-none-any\n",
        f"{dist}-{version}.dist-info/RECORD": b"",
    }
    if license_file:
        members[f"{dist}-{version}.dist-info/licenses/LICENSE.txt"] = b"MIT License\n"
    members.update(extra or {})
    with zipfile.ZipFile(path, "w") as archive:
        for member, data in members.items():
            archive.writestr(member, data)


def _official_licenses(root: Path):
    qt = root / "_official" / "Qt-PySide6-6.11.1"
    qt.mkdir(parents=True)
    for name in (
        "LGPL-3.0-only.txt",
        "GPL-3.0-only.txt",
        "GPL-2.0-only.txt",
        "Qt-GPL-exception-1.0.txt",
    ):
        (qt / name).write_text(f"official {name}\n", encoding="utf-8")


def test_filter_pyside_removes_gpl_only_payload_and_rebuilds_record(tmp_path):
    wheelhouse = tmp_path / "wheelhouse"
    wheelhouse.mkdir()
    wheel = wheelhouse / "PySide6_Essentials-6.11.1-py3-none-any.whl"
    _wheel(
        wheel,
        "PySide6_Essentials",
        "6.11.1",
        extra={
            "PySide6/QtCore.pyd": b"unchanged",
            "PySide6/Qt6Lottie.dll": b"remove",
            "PySide6/qml/QtQuick/VirtualKeyboard/qmldir": b"remove",
        },
    )
    provenance = tmp_path / "provenance.json"

    compliance.filter_pyside(wheelhouse, provenance)

    details = json.loads(provenance.read_text(encoding="utf-8"))
    assert details["library_binaries_modified"] is False
    assert "PySide6/Qt6Lottie.dll" in details["removed_paths"]
    with zipfile.ZipFile(wheel) as archive:
        assert archive.read("PySide6/QtCore.pyd") == b"unchanged"
        assert not any(compliance.is_forbidden_qt_path(n) for n in archive.namelist())
        record = next(n for n in archive.namelist() if n.endswith(".dist-info/RECORD"))
        rows = list(csv.reader(io.StringIO(archive.read(record).decode())))
        assert any(row[0] == "PySide6/QtCore.pyd" and row[1] for row in rows)


def test_collect_wheels_fails_closed_when_license_file_is_missing(tmp_path):
    wheelhouse = tmp_path / "wheelhouse"
    wheelhouse.mkdir()
    _wheel(wheelhouse / "example-1.0-py3-none-any.whl", license_file=False)
    licenses = tmp_path / "licenses"
    _official_licenses(licenses)
    provenance = tmp_path / "provenance.json"
    provenance.write_text(
        json.dumps({"package": "Example", "version": "1.0"}), encoding="utf-8"
    )

    with pytest.raises(compliance.ComplianceError, match="no .dist-info license"):
        compliance.collect_wheels(
            wheelhouse, licenses, tmp_path / "manifest.json", provenance
        )


def test_wheel_path_traversal_is_rejected(tmp_path):
    wheel = tmp_path / "bad.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("../LICENSE", "bad")
    with zipfile.ZipFile(wheel) as archive:
        with pytest.raises(compliance.ComplianceError, match="unsafe wheel member"):
            compliance.safe_members(archive)


def test_verify_bundle_requires_manifest_coverage_and_rejects_dicom(tmp_path):
    bundle = tmp_path / "bundle"
    (bundle / "wheelhouse").mkdir(parents=True)
    (bundle / "THIRD_PARTY_LICENSES").mkdir()
    (bundle / "LICENSE").write_text("MIT", encoding="utf-8")
    (bundle / "NOTICE.txt").write_text("notice", encoding="utf-8")
    (bundle / "THIRD_PARTY_MANIFEST.json").write_text(
        json.dumps({"packages": []}), encoding="utf-8"
    )
    compliance.verify_bundle(bundle)

    (bundle / "patient.dcm").write_bytes(b"DICM")
    with pytest.raises(compliance.ComplianceError, match="patient/local-data"):
        compliance.verify_bundle(bundle)


def test_verify_bundle_rejects_preambleless_dicom_with_unknown_suffix(tmp_path):
    bundle = tmp_path / "bundle"
    (bundle / "wheelhouse").mkdir(parents=True)
    (bundle / "THIRD_PARTY_LICENSES").mkdir()
    (bundle / "LICENSE").write_text("MIT", encoding="utf-8")
    (bundle / "NOTICE.txt").write_text("notice", encoding="utf-8")
    (bundle / "THIRD_PARTY_MANIFEST.json").write_text(
        json.dumps({"packages": []}), encoding="utf-8"
    )

    def element(group, item, vr, value):
        if len(value) % 2:
            value += b"\0" if vr == b"UI" else b" "
        return struct.pack("<HH2sH", group, item, vr, len(value)) + value

    dataset = b"".join(
        (
            element(0x0008, 0x0016, b"UI", b"1.2.840.10008.5.1.4.1.1.481.2"),
            element(0x0008, 0x0018, b"UI", b"1.2.826.0.1.3680043.8.498.1"),
            element(0x0008, 0x0060, b"CS", b"RTDOSE"),
        )
    )
    (bundle / "opaque_payload.bin").write_bytes(dataset)

    with pytest.raises(compliance.ComplianceError, match="DICOM payload"):
        compliance.verify_bundle(bundle)


def test_verify_bundle_rejects_nested_archive_with_disguised_suffix(tmp_path):
    bundle = tmp_path / "bundle"
    (bundle / "wheelhouse").mkdir(parents=True)
    (bundle / "THIRD_PARTY_LICENSES").mkdir()
    (bundle / "LICENSE").write_text("MIT", encoding="utf-8")
    (bundle / "NOTICE.txt").write_text("notice", encoding="utf-8")
    (bundle / "THIRD_PARTY_MANIFEST.json").write_text(
        json.dumps({"packages": []}), encoding="utf-8"
    )
    with zipfile.ZipFile(bundle / "patient_export.bin", "w") as archive:
        archive.writestr("patient.dcm", b"\0" * 128 + b"DICM")

    with pytest.raises(compliance.ComplianceError, match=r"nested archive \(zip\)"):
        compliance.verify_bundle(bundle)


def test_verify_bundle_rejects_unverified_wheel_outside_wheelhouse(tmp_path):
    bundle = tmp_path / "bundle"
    (bundle / "wheelhouse").mkdir(parents=True)
    (bundle / "THIRD_PARTY_LICENSES").mkdir()
    (bundle / "app").mkdir()
    (bundle / "LICENSE").write_text("MIT", encoding="utf-8")
    (bundle / "NOTICE.txt").write_text("notice", encoding="utf-8")
    (bundle / "THIRD_PARTY_MANIFEST.json").write_text(
        json.dumps({"packages": []}), encoding="utf-8"
    )
    with zipfile.ZipFile(bundle / "app" / "patient_export.whl", "w") as archive:
        archive.writestr("patient.dcm", b"\0" * 128 + b"DICM")

    with pytest.raises(compliance.ComplianceError, match="unverified wheel"):
        compliance.verify_bundle(bundle)


def test_verify_bundle_rejects_executable_outside_pinned_python_path(tmp_path):
    bundle = tmp_path / "bundle"
    (bundle / "wheelhouse").mkdir(parents=True)
    (bundle / "THIRD_PARTY_LICENSES").mkdir()
    (bundle / "app" / "python").mkdir(parents=True)
    (bundle / "LICENSE").write_text("MIT", encoding="utf-8")
    (bundle / "NOTICE.txt").write_text("notice", encoding="utf-8")
    (bundle / "THIRD_PARTY_MANIFEST.json").write_text(
        json.dumps({"packages": []}), encoding="utf-8"
    )
    (bundle / "app" / "python" / "untrusted.exe").write_bytes(b"MZ")

    with pytest.raises(compliance.ComplianceError, match="unexpected executable"):
        compliance.verify_bundle(bundle)


def test_verify_bundle_rejects_secret_material(tmp_path):
    bundle = tmp_path / "bundle"
    (bundle / "wheelhouse").mkdir(parents=True)
    (bundle / "THIRD_PARTY_LICENSES").mkdir()
    (bundle / "LICENSE").write_text("MIT", encoding="utf-8")
    (bundle / "NOTICE.txt").write_text("notice", encoding="utf-8")
    (bundle / "THIRD_PARTY_MANIFEST.json").write_text(
        json.dumps({"packages": []}), encoding="utf-8"
    )
    (bundle / "notes.txt").write_bytes(b"-----BEGIN PRIVATE KEY-----")
    with pytest.raises(compliance.ComplianceError, match="secret marker"):
        compliance.verify_bundle(bundle)


def test_fast_viewer_dependency_avoids_meta_package_and_addons():
    root = Path(__file__).parents[1]
    requirements = (root / "requirements-fast-viewer.txt").read_text(encoding="utf-8")
    constraints = (root / "offline/constraints-py312-win64.txt").read_text(
        encoding="utf-8"
    )
    active = [
        line.strip().lower()
        for line in (requirements + "\n" + constraints).splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    assert any(line.startswith("pyside6_essentials") for line in active)
    assert not any(line.startswith("pyside6==") for line in active)
    assert not any(line.startswith("pyside6_addons") for line in active)


def test_root_mit_license_has_expected_owner():
    root = Path(__file__).parents[1]
    license_text = (root / "LICENSE").read_text(encoding="utf-8")
    assert "Copyright (c) 2026 Hiroki Inata" in license_text
    assert "Permission is hereby granted, free of charge" in license_text
    notice_text = (root / "offline/NOTICE.txt").read_text(encoding="utf-8")
    assert "Hiroki Inata <169@inata169.com>" in notice_text
