import subprocess
from types import SimpleNamespace

import pytest

from omni_driver.connector.adb import ADB
from omni_driver.connector.base import Connector
from omni_driver.errors import DeviceCommandError


class _Connector(Connector):
    def run_cmd(self, extra_args):
        return self._check_output(extra_args)

    def shell(self, extra_args):
        return self.run_cmd(extra_args)


def test_adb_devices_only_returns_ready_devices(monkeypatch):
    output = b"""List of devices attached
emulator-5554\tdevice product:sdk_gphone
R58M123\tunauthorized
192.168.0.8:5555\toffline
"""
    monkeypatch.setattr("omni_driver.connector.adb.subprocess.check_output", lambda *_a, **_kw: output)

    assert ADB.device_states() == {
        "emulator-5554": "device",
        "R58M123": "unauthorized",
        "192.168.0.8:5555": "offline",
    }
    assert ADB.devices() == ["emulator-5554"]


def test_adb_shell_preserves_remote_expression(monkeypatch):
    connector = ADB(SimpleNamespace(serial="emulator-5554"))
    captured = {}
    monkeypatch.setattr(
        connector,
        "_check_output",
        lambda args: captured.setdefault("args", args) or "",
    )

    connector.shell("echo 'hello world' && getprop ro.product.model")

    assert captured["args"] == [
        "adb",
        "-s",
        "emulator-5554",
        "shell",
        "echo 'hello world' && getprop ro.product.model",
    ]


def test_connector_normalizes_missing_executable(monkeypatch):
    def missing(*_args, **_kwargs):
        raise FileNotFoundError("adb")

    monkeypatch.setattr("omni_driver.connector.base.subprocess.check_output", missing)

    with pytest.raises(DeviceCommandError, match="executable not found: adb"):
        _Connector().run_cmd(["adb", "devices"])


def test_connector_normalizes_nonzero_exit(monkeypatch):
    def failed(args, **_kwargs):
        raise subprocess.CalledProcessError(1, args, output=b"permission denied")

    monkeypatch.setattr("omni_driver.connector.base.subprocess.check_output", failed)

    with pytest.raises(DeviceCommandError, match="permission denied"):
        _Connector().run_cmd(["adb", "devices"])
