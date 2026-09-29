import copy
import json
import os
import socket

import pytest

FIXTURES = os.path.join(os.path.dirname(__file__), 'fixtures')


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Unit tests make zero network requests: any socket connect fails."""

    def refuse(*args, **kwargs):
        raise AssertionError('network access attempted in a unit test: %r' % (args[1:],))

    monkeypatch.setattr(socket.socket, 'connect', refuse)
    monkeypatch.setattr(socket.socket, 'connect_ex', refuse)
    monkeypatch.setattr(socket, 'create_connection', refuse)
    monkeypatch.setattr(socket, 'getaddrinfo', refuse)


class FakeYoutubeDL(object):
    """Stands in for yt_dlp.YoutubeDL; returns a canned info dict."""

    def __init__(self, info=None, error=None):
        self.info = info
        self.error = error
        self.calls = []

    def extract_info(self, url, download=True, process=True):
        self.calls.append((url, download, process))
        if self.error is not None:
            raise self.error
        return copy.deepcopy(self.info)


def _load(name):
    with open(os.path.join(FIXTURES, name + '.json')) as f:
        return json.load(f)


@pytest.fixture
def load_info():
    return _load


@pytest.fixture
def fake_ydl():
    return FakeYoutubeDL
