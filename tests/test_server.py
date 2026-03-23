from __future__ import annotations

from pathlib import Path
from socketserver import TCPServer
from threading import Thread
from time import sleep

from pytest import fixture, mark

from skillbridge.client.channel import create_channel_class
from skillbridge.server import python_server

WORKSPACE_ID = '23210'
channel_class = create_channel_class()
tcp_channel_class = create_channel_class(force_tcp=True)


class Redirect:
    def __init__(self) -> None:
        self.written = []
        self.reading = []

    def prepare(self, message):
        self.reading.append(message)

    def pop(self):
        try:
            return self.written.pop()
        except IndexError:
            return None

    def write(self, message):
        self.written.append(message)

    def read(self, _timeout=None):
        return self.reading.pop()


class Server(Thread):
    def __init__(self, use_tcp: bool = False) -> None:
        self.use_tcp = use_tcp
        self.server: TCPServer | None = None
        super().__init__(daemon=True)

    def start(self) -> None:
        super().start()

    def run(self):
        with python_server.create_server(
            WORKSPACE_ID,
            "DEBUG",
            single=False,
            timeout=None,
            force_tcp=self.use_tcp,
        ) as server:
            print("HI FROM SERVER")
            python_server.send_to_skill('running')
            self.server = server
            server.serve_forever()

    def join(self, timeout: float | None = None) -> None:
        if self.server:
            self.server.shutdown()
        return super().join(timeout)


@fixture
def redirect():
    send = python_server.send_to_skill
    read = python_server.read_from_skill

    r = Redirect()
    python_server.send_to_skill = r.write
    python_server.read_from_skill = r.read
    try:
        yield r
    finally:
        python_server.send_to_skill = send
        python_server.read_from_skill = read
        Path(channel_class.create_address(WORKSPACE_ID)).unlink(missing_ok=True)


@mark.parametrize("use_tcp", argvalues=[False, True], ids=["unix", "tcp"])
def test_server_notifies(redirect: Redirect, use_tcp: bool):
    s = Server(use_tcp=use_tcp)
    s.start()
    sleep(2)
    assert redirect.pop() == 'running', "Server didn't start in time"

    c = (tcp_channel_class if use_tcp else channel_class)(WORKSPACE_ID)
    c.close()

    s.join()


@mark.parametrize("use_tcp", argvalues=[False, True], ids=["unix", "tcp"])
def test_one_request(redirect: Redirect, use_tcp: bool):
    s = Server(use_tcp=use_tcp)
    s.start()
    sleep(2)

    c = (tcp_channel_class if use_tcp else channel_class)(WORKSPACE_ID)
    redirect.prepare('success pong')
    response = c.send('ping')
    assert response == 'pong'

    c.close()
    s.join()
