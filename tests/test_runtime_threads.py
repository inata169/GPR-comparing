import logging
import sys
from types import SimpleNamespace

import pytest

from rtgamma.main import _configure_numba_threads


def test_numba_thread_limit_is_applied(monkeypatch):
    calls = []
    fake_numba = SimpleNamespace(
        set_num_threads=calls.append,
        get_num_threads=lambda: calls[-1],
        config=SimpleNamespace(NUMBA_NUM_THREADS=16),
    )
    monkeypatch.setitem(sys.modules, 'numba', fake_numba)

    assert _configure_numba_threads('numba', 8) is True
    assert calls == [8]


def test_threads_zero_means_automatic(monkeypatch):
    monkeypatch.setitem(
        sys.modules,
        'numba',
        SimpleNamespace(set_num_threads=lambda _: pytest.fail('must not be called')),
    )

    assert _configure_numba_threads('numba', 0) is False


def test_pymedphys_logs_that_threads_are_not_applied(caplog):
    caplog.set_level(logging.WARNING)

    assert _configure_numba_threads('pymedphys', 8) is False
    assert 'is not applied by the PyMedPhys engine' in caplog.text


def test_negative_thread_count_is_rejected():
    with pytest.raises(ValueError, match=r'0 \(automatic\) or a positive integer'):
        _configure_numba_threads('numba', -1)
