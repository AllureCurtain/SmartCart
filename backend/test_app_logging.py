import logging
import sys

import app_logging


class _DummyStream:
    def __init__(self):
        self.encoding = 'gbk'
        self.reconfigured = []

    def write(self, data):
        return len(data)

    def flush(self):
        return None

    def reconfigure(self, **kwargs):
        self.reconfigured.append(kwargs)
        if 'encoding' in kwargs:
            self.encoding = kwargs['encoding']


def test_setup_logging_reconfigures_stdout_to_utf8(monkeypatch):
    dummy_out = _DummyStream()
    dummy_err = _DummyStream()
    monkeypatch.setattr(sys, 'stdout', dummy_out)
    monkeypatch.setattr(sys, 'stderr', dummy_err)

    root = logging.getLogger()
    old_handlers = root.handlers[:]
    root.handlers.clear()
    try:
        app_logging.setup_logging()
        assert dummy_out.encoding == 'utf-8'
        assert dummy_out.reconfigured
        assert root.handlers
    finally:
        root.handlers[:] = old_handlers
