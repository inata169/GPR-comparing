"""Fail-closed license preparation and verification for distribution bundles.

Wheels are treated only as ZIP archives.  No code from a wheel is imported or
executed by this module.
"""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import io
import json
import os
import re
import shutil
import sys
import urllib.request
import zipfile
from email.parser import BytesParser
from email.policy import compat32
from pathlib import Path, PurePosixPath

LICENSE_NAMES = re.compile(
    r"(^|/)(licen[cs]e|copying|notice|copyright|authors?)[^/]*$",
    re.IGNORECASE,
)
QT_PACKAGES = {"pyside6_essentials", "shiboken6"}
FORBIDDEN_QT_TOKENS = (
    "canvaspainter",
    "qtcoap",
    "qtgraphs",
    "qtgrpc",
    "httpserver",
    "lottie",
    "qtmqtt",
    "networkauth",
    "qmlcompiler",
    "quick3d",
    "quicktimeline",
    "virtualkeyboard",
    "waylandcompositor",
)
FORBIDDEN_PACKAGE_NAMES = {"pyside6", "pyside6_addons"}
REQUIRED_ROOT_FILES = (
    "LICENSE",
    "NOTICE.txt",
    "THIRD_PARTY_LICENSES",
    "THIRD_PARTY_MANIFEST.json",
)
FORBIDDEN_BUNDLE_SUFFIXES = (".dcm", ".dcm30", ".nii", ".nii.gz")
FORBIDDEN_BUNDLE_NAMES = (
    ".env",
    "credentials.json",
    "id_rsa",
    "id_ed25519",
    "gui_config.ini",
)
FORBIDDEN_SECRET_SUFFIXES = (".key", ".p12", ".pem", ".pfx")
FORBIDDEN_APP_DIRECTORIES = (
    "app/dicom/",
    "app/output/",
    "app/phits-linac-validation/",
)
SECRET_MARKERS = (
    b"-----BEGIN " + b"PRIVATE KEY-----",
    b"-----BEGIN " + b"OPENSSH PRIVATE KEY-----",
    b"github_" + b"pat_",
    b"gh" + b"p_",
)


class ComplianceError(RuntimeError):
    """A release-blocking compliance problem."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalized(value: str) -> str:
    return re.sub(r"[-_.]+", "_", value).lower()


def field_text(value) -> str:
    """Return an email metadata field as plain text across metadata versions."""
    return str(value).strip() if value is not None else ""


def safe_members(archive: zipfile.ZipFile) -> list[zipfile.ZipInfo]:
    seen: set[str] = set()
    result = []
    for info in archive.infolist():
        name = info.filename.replace("\\", "/")
        pure = PurePosixPath(name)
        if pure.is_absolute() or ".." in pure.parts or not pure.parts:
            raise ComplianceError(f"unsafe wheel member: {name}")
        key = name.casefold()
        if key in seen:
            raise ComplianceError(f"duplicate wheel member: {name}")
        if (info.external_attr >> 16) & 0o170000 == 0o120000:
            raise ComplianceError(f"wheel symlink is not accepted: {name}")
        seen.add(key)
        result.append(info)
    return result


def metadata_from_wheel(
    archive: zipfile.ZipFile, members: list[zipfile.ZipInfo]
):
    paths = [m for m in members if m.filename.endswith(".dist-info/METADATA")]
    if len(paths) != 1:
        raise ComplianceError(
            f"wheel must contain exactly one .dist-info/METADATA; found {len(paths)}"
        )
    return BytesParser(policy=compat32).parsebytes(archive.read(paths[0])), paths[0]


def is_forbidden_qt_path(name: str) -> bool:
    # Ignore Qt's major-version digit (for example Qt6Lottie.dll) as well as
    # separators so the same rules cover binaries, bindings and QML payloads.
    compact = re.sub(r"[^a-z]", "", name.lower())
    return any(token in compact for token in FORBIDDEN_QT_TOKENS)


def filter_pyside(wheelhouse: Path, provenance_path: Path) -> None:
    candidates = sorted(wheelhouse.glob("PySide6_Essentials-6.11.1-*.whl"))
    if len(candidates) != 1:
        raise ComplianceError(
            "expected exactly one PySide6_Essentials 6.11.1 wheel; "
            f"found {len(candidates)}"
        )
    wheel = candidates[0]
    upstream_hash = sha256_file(wheel)
    output = wheel.with_suffix(".filtered.whl")
    removed: list[str] = []
    with zipfile.ZipFile(wheel, "r") as source:
        members = safe_members(source)
        metadata, metadata_info = metadata_from_wheel(source, members)
        if normalized(metadata.get("Name", "")) != "pyside6_essentials":
            raise ComplianceError("unexpected package in the Essentials wheel")
        record_names = [m.filename for m in members if m.filename.endswith(".dist-info/RECORD")]
        if len(record_names) != 1:
            raise ComplianceError("Essentials wheel must contain exactly one RECORD")
        record_name = record_names[0]
        rows: list[tuple[str, str, str]] = []
        kept: list[tuple[zipfile.ZipInfo, bytes]] = []
        with zipfile.ZipFile(output, "w", allowZip64=True) as target:
            for info in members:
                name = info.filename
                if name == record_name:
                    continue
                if is_forbidden_qt_path(name):
                    removed.append(name)
                    continue
                data = source.read(info)
                target.writestr(info, data)
                encoded = base64.urlsafe_b64encode(
                    hashlib.sha256(data).digest()
                ).rstrip(b"=").decode("ascii")
                rows.append((name, f"sha256={encoded}", str(len(data))))
            record_buffer = io.StringIO(newline="")
            writer = csv.writer(record_buffer, lineterminator="\n")
            writer.writerows(rows)
            writer.writerow((record_name, "", ""))
            record_data = record_buffer.getvalue().encode("utf-8")
            target.writestr(record_name, record_data)
    if not removed:
        output.unlink(missing_ok=True)
        raise ComplianceError("no GPL-only Qt payload was found; review version rules")
    with zipfile.ZipFile(output, "r") as filtered:
        leftovers = [n for n in filtered.namelist() if is_forbidden_qt_path(n)]
        if leftovers:
            output.unlink(missing_ok=True)
            raise ComplianceError(f"GPL-only Qt payload remains: {leftovers}")
        metadata, _ = metadata_from_wheel(filtered, safe_members(filtered))
        if metadata.get("Version") != "6.11.1":
            raise ComplianceError("unexpected Essentials version after filtering")
    os.replace(output, wheel)
    provenance_path.parent.mkdir(parents=True, exist_ok=True)
    provenance_path.write_text(
        json.dumps(
            {
                "package": "PySide6_Essentials",
                "version": "6.11.1",
                "upstream_wheel": wheel.name,
                "upstream_sha256": upstream_hash,
                "bundled_sha256": sha256_file(wheel),
                "archive_modified": True,
                "library_binaries_modified": False,
                "reason": "Removed unused Qt modules listed by Qt as GPL-only.",
                "removed_paths": sorted(removed),
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )


def fetch_resources(config_path: Path, output: Path) -> None:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    resources = config.get("resources")
    if not isinstance(resources, list) or not resources:
        raise ComplianceError("license resource list is empty")
    for resource in resources:
        relative = PurePosixPath(resource["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ComplianceError(f"unsafe resource path: {relative}")
        destination = output.joinpath(*relative.parts)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(resource["url"], timeout=60) as response:
            data = response.read()
        actual = sha256_bytes(data)
        if actual != resource["sha256"].lower():
            raise ComplianceError(
                f"official license resource hash mismatch: {resource['path']} "
                f"expected {resource['sha256']}, got {actual}"
            )
        destination.write_bytes(data)


def license_identity(metadata) -> tuple[str, list[str]]:
    expression = field_text(metadata.get("License-Expression"))
    legacy = field_text(metadata.get("License"))
    classifiers = [
        field_text(value)
        for value in metadata.get_all("Classifier", [])
        if field_text(value).startswith("License ::")
    ]
    candidates = [value for value in (expression, legacy) if value]
    candidates.extend(classifiers)
    meaningful = [
        value for value in candidates if value.lower() not in {"unknown", "none", "n/a"}
    ]
    if not meaningful:
        raise ComplianceError(
            f"license is missing or unknown for {metadata.get('Name', '<unknown>')}"
        )
    return meaningful[0], classifiers


def project_urls(metadata) -> list[str]:
    urls = []
    for value in metadata.get_all("Project-URL", []):
        value = field_text(value)
        if "," in value:
            label, url = value.split(",", 1)
            urls.append(f"{label.strip()}: {url.strip()}")
        else:
            urls.append(value.strip())
    home = field_text(metadata.get("Home-page"))
    if home:
        urls.append(f"Home-page: {home}")
    return sorted(set(urls))


def collect_wheels(
    wheelhouse: Path,
    output: Path,
    manifest_path: Path,
    provenance_path: Path,
) -> None:
    wheels = sorted(wheelhouse.glob("*.whl"))
    if not wheels:
        raise ComplianceError("wheelhouse contains no wheels")
    official = output / "_official"
    qt_official = official / "Qt-PySide6-6.11.1"
    required_qt = (
        "LGPL-3.0-only.txt",
        "GPL-3.0-only.txt",
        "GPL-2.0-only.txt",
        "Qt-GPL-exception-1.0.txt",
    )
    for name in required_qt:
        if not (qt_official / name).is_file():
            raise ComplianceError(f"required official Qt license is missing: {name}")
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    entries = []
    names = set()
    for wheel in wheels:
        with zipfile.ZipFile(wheel, "r") as archive:
            members = safe_members(archive)
            metadata, metadata_info = metadata_from_wheel(archive, members)
            name = field_text(metadata.get("Name"))
            version = field_text(metadata.get("Version"))
            if not name or not version:
                raise ComplianceError(f"name/version missing in {wheel.name}")
            key = normalized(name)
            if key in names:
                raise ComplianceError(f"duplicate distribution: {name}")
            if key in FORBIDDEN_PACKAGE_NAMES:
                raise ComplianceError(f"forbidden Qt package in wheelhouse: {name}")
            names.add(key)
            license_value, classifiers = license_identity(metadata)
            license_members = [
                m
                for m in members
                if ".dist-info/" in m.filename
                and LICENSE_NAMES.search(m.filename)
                and not m.is_dir()
            ]
            if not license_members:
                raise ComplianceError(f"no .dist-info license material in {wheel.name}")
            forbidden_paths = (
                [m.filename for m in members if is_forbidden_qt_path(m.filename)]
                if key in QT_PACKAGES
                else []
            )
            if forbidden_paths:
                raise ComplianceError(
                    f"GPL-only Qt payload remains in {wheel.name}: {forbidden_paths[:5]}"
                )
            package_dir = output / f"{name}-{version}"
            package_dir.mkdir(parents=True, exist_ok=False)
            copied = []
            for member in license_members:
                relative = PurePosixPath(member.filename)
                destination = package_dir / "wheel-metadata" / Path(*relative.parts)
                destination.parent.mkdir(parents=True, exist_ok=True)
                data = archive.read(member)
                if not data.strip():
                    raise ComplianceError(f"empty license material: {member.filename}")
                destination.write_bytes(data)
                copied.append(destination.relative_to(output).as_posix())
            metadata_out = package_dir / "METADATA.txt"
            metadata_out.write_bytes(archive.read(metadata_info))
            copied.append(metadata_out.relative_to(output).as_posix())
            if key in QT_PACKAGES:
                for source in sorted(qt_official.iterdir()):
                    destination = package_dir / "official-qt-licenses" / source.name
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, destination)
                    copied.append(destination.relative_to(output).as_posix())
            source_urls = project_urls(metadata)
            source_urls.append(f"PyPI: https://pypi.org/project/{name}/{version}/")
            entries.append(
                {
                    "name": name,
                    "version": version,
                    "wheel": wheel.name,
                    "wheel_sha256": sha256_file(wheel),
                    "license": license_value,
                    "license_classifiers": classifiers,
                    "distribution_sources": sorted(set(source_urls)),
                    "license_files": sorted(copied),
                    "requires_dist": [
                        field_text(value)
                        for value in metadata.get_all("Requires-Dist", [])
                    ],
                }
            )
    if normalized(provenance["package"]) not in names:
        raise ComplianceError("PySide6 filtering provenance has no matching wheel")
    manifest = {
        "schema_version": 1,
        "generated_from": "wheel .dist-info metadata; package names were not used to infer licenses",
        "publisher": {
            "name": "Hiroki Inata",
            "email": "169@inata169.com",
        },
        "packages": sorted(entries, key=lambda item: normalized(item["name"])),
        "pyside6_qt": {
            "community_edition": True,
            "used_modules": ["QtCore", "QtGui", "QtWidgets"],
            "gpl_only_modules_bundled": False,
            "filter_provenance": provenance,
            "qt_source": "https://code.qt.io/cgit/qt/",
            "pyside_source": "https://code.qt.io/cgit/pyside/pyside-setup.git/",
        },
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def verify_bundle(bundle: Path) -> None:
    for name in REQUIRED_ROOT_FILES:
        if not (bundle / name).exists():
            raise ComplianceError(f"required bundle item is missing: {name}")
    manifest = json.loads((bundle / "THIRD_PARTY_MANIFEST.json").read_text(encoding="utf-8"))
    entries = manifest.get("packages", [])
    by_wheel = {entry["wheel"]: entry for entry in entries}
    wheels = sorted((bundle / "wheelhouse").glob("*.whl"))
    if set(by_wheel) != {wheel.name for wheel in wheels}:
        raise ComplianceError("wheelhouse and THIRD_PARTY_MANIFEST.json do not match")
    for wheel in wheels:
        entry = by_wheel[wheel.name]
        if sha256_file(wheel) != entry["wheel_sha256"]:
            raise ComplianceError(f"manifest wheel hash mismatch: {wheel.name}")
        if not entry.get("license") or not entry.get("license_files"):
            raise ComplianceError(f"incomplete license manifest entry: {wheel.name}")
        for relative in entry["license_files"]:
            if not (bundle / "THIRD_PARTY_LICENSES" / relative).is_file():
                raise ComplianceError(f"missing collected license file: {relative}")
        with zipfile.ZipFile(wheel, "r") as archive:
            members = safe_members(archive)
            if normalized(entry["name"]) in QT_PACKAGES and any(
                is_forbidden_qt_path(member.filename) for member in members
            ):
                raise ComplianceError(f"GPL-only Qt content found in {wheel.name}")
    for path in bundle.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(bundle).as_posix().lower()
        name = path.name.lower()
        if any(relative.startswith(prefix) for prefix in FORBIDDEN_APP_DIRECTORIES):
            raise ComplianceError(f"forbidden application data directory: {relative}")
        if (
            name in FORBIDDEN_BUNDLE_NAMES
            or name.startswith(".env.")
            or name.startswith("secret")
            or name.endswith(FORBIDDEN_SECRET_SUFFIXES)
            or any(
            relative.endswith(suffix) for suffix in FORBIDDEN_BUNDLE_SUFFIXES
            )
        ):
            raise ComplianceError(f"forbidden patient/local-data file: {relative}")
        if name.endswith(".exe") and path.parent.name.lower() != "python":
            raise ComplianceError(f"unexpected executable in bundle: {relative}")
        if any(token in name for token in ("phits.exe", "sumtally.exe", "phits2dicom.exe")):
            raise ComplianceError(f"forbidden PHITS-related executable: {relative}")
        if path.suffix.lower() not in {".whl", ".exe", ".png", ".jpg", ".pdf"}:
            data = path.read_bytes()
            if len(data) >= 132 and data[128:132] == b"DICM":
                raise ComplianceError(f"DICOM payload found in bundle: {relative}")
            if any(marker in data for marker in SECRET_MARKERS):
                raise ComplianceError(f"secret marker found in bundle: {relative}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    fetch = subparsers.add_parser("fetch-resources")
    fetch.add_argument("--config", type=Path, required=True)
    fetch.add_argument("--output", type=Path, required=True)
    filt = subparsers.add_parser("filter-pyside")
    filt.add_argument("--wheelhouse", type=Path, required=True)
    filt.add_argument("--provenance", type=Path, required=True)
    collect = subparsers.add_parser("collect-wheels")
    collect.add_argument("--wheelhouse", type=Path, required=True)
    collect.add_argument("--output", type=Path, required=True)
    collect.add_argument("--manifest", type=Path, required=True)
    collect.add_argument("--provenance", type=Path, required=True)
    verify = subparsers.add_parser("verify-bundle")
    verify.add_argument("--bundle", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        if args.command == "fetch-resources":
            fetch_resources(args.config, args.output)
        elif args.command == "filter-pyside":
            filter_pyside(args.wheelhouse, args.provenance)
        elif args.command == "collect-wheels":
            collect_wheels(args.wheelhouse, args.output, args.manifest, args.provenance)
        elif args.command == "verify-bundle":
            verify_bundle(args.bundle)
    except (ComplianceError, KeyError, OSError, ValueError, zipfile.BadZipFile) as exc:
        print(f"LICENSE COMPLIANCE ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
