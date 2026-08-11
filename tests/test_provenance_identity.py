import json
import sys

from rtgamma.provenance import _application_identity


def test_frozen_application_identity_uses_packaged_sidecar(monkeypatch, tmp_path):
    executable = tmp_path / 'rtgamma_cli.exe'
    executable.touch()
    (tmp_path / 'application_identity.json').write_text(
        json.dumps(
            {
                'schema_version': 1,
                'version': '0.9.1-test',
                'git_commit': '0123456789abcdef',
                'git_dirty': False,
            }
        ),
        encoding='utf-8',
    )
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(sys, 'executable', str(executable))
    monkeypatch.delenv('GPR_COMPARING_VERSION', raising=False)

    identity = _application_identity()

    assert identity == {
        'name': 'GPR-comparing',
        'version': '0.9.1-test',
        'version_source': 'packaged-build',
        'git_commit': '0123456789abcdef',
        'git_dirty': False,
    }
