import os
import shlex
import subprocess

from loguru import logger

from .._config import positive_float_env
from ..errors import DeviceCommandError
from .base import (
    Connector,
    DEFAULT_DEVICE_COMMAND_TIMEOUT,
    DeviceCommandTimeoutError,
)


ADB_COMMAND_TIMEOUT = positive_float_env(
    "ADB_COMMAND_TIMEOUT",
    DEFAULT_DEVICE_COMMAND_TIMEOUT,
)


class ADB(Connector):
    def __init__(self, device=None):
        if device is None:
            raise ValueError("device is required")
        super().__init__(device, command_timeout=ADB_COMMAND_TIMEOUT)
        self.serial = device.serial
        self.cmd_prefix = ["adb", "-s", self.serial]

    def run_cmd(self, extra_args):
        args = self._normalize_args(extra_args)
        return self._check_output(self.cmd_prefix + args)

    def shell(self, extra_args):
        if not isinstance(extra_args, str):
            raise TypeError("shell args must be str")
        # Keep the remote shell expression intact so quotes and spaces survive.
        return self.run_cmd(["shell", extra_args])

    @classmethod
    def devices(cls):
        states = cls.device_states()
        devices = [serial for serial, state in states.items() if state == "device"]
        logger.debug("adb devices: {}", devices)
        return devices

    @classmethod
    def device_states(cls):
        try:
            result = subprocess.check_output(
                ["adb", "devices"],
                timeout=ADB_COMMAND_TIMEOUT,
            ).strip()
        except subprocess.TimeoutExpired as exc:
            raise DeviceCommandTimeoutError(
                f"adb devices timed out after {ADB_COMMAND_TIMEOUT:g}s"
            ) from exc
        except FileNotFoundError as exc:
            raise DeviceCommandError("required executable not found: adb") from exc
        except subprocess.CalledProcessError as exc:
            raise DeviceCommandError(
                f"adb devices failed with exit code {exc.returncode}"
            ) from exc
        if not isinstance(result, str):
            result = result.decode(errors="replace")
        states = {}
        for line in result.splitlines():
            line = line.strip()
            if not line or line.startswith("List of devices attached"):
                continue
            columns = line.split()
            if len(columns) < 2:
                continue
            serial, state = columns[0], columns[1].lower()
            states[serial] = state
        logger.debug("adb device states: {}", states)
        return states

    @staticmethod
    def _normalize_args(extra_args):
        if isinstance(extra_args, str):
            return shlex.split(extra_args, posix=os.name != "nt")
        if isinstance(extra_args, (list, tuple)):
            return [str(arg) for arg in extra_args]
        raise TypeError("command args must be str, list, or tuple")
