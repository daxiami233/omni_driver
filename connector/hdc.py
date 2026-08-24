import os
import shlex
import subprocess

from loguru import logger

from ..errors import DeviceCommandError
from .base import (
    Connector,
    DEFAULT_DEVICE_COMMAND_TIMEOUT,
    DeviceCommandTimeoutError,
)


class HDC(Connector):
    def __init__(self, device=None):
        if device is None:
            raise ValueError("device is required")
        super().__init__(device)
        self.serial = device.serial
        self.cmd_prefix = ["hdc", "-t", self.serial]

    def run_cmd(self, extra_args):
        args = self._normalize_args(extra_args)
        return self._check_output(self.cmd_prefix + args)

    def shell(self, extra_args):
        if not isinstance(extra_args, str):
            raise TypeError("shell args must be str")
        return self.run_cmd(["shell", extra_args])

    @classmethod
    def devices(cls):
        try:
            result = subprocess.check_output(
                ["hdc", "list", "targets"],
                timeout=DEFAULT_DEVICE_COMMAND_TIMEOUT,
            ).strip()
        except subprocess.TimeoutExpired as exc:
            raise DeviceCommandTimeoutError(
                f"hdc list targets timed out after {DEFAULT_DEVICE_COMMAND_TIMEOUT:g}s"
            ) from exc
        except FileNotFoundError as exc:
            raise DeviceCommandError("required executable not found: hdc") from exc
        except subprocess.CalledProcessError as exc:
            raise DeviceCommandError(
                f"hdc list targets failed with exit code {exc.returncode}"
            ) from exc
        if not isinstance(result, str):
            result = result.decode(errors="replace")
        devices = [line.strip() for line in result.splitlines() if line.strip() and line.strip() != "[Empty]"]
        logger.debug("hdc devices: {}", devices)
        return devices

    @staticmethod
    def _normalize_args(extra_args):
        if isinstance(extra_args, str):
            return shlex.split(extra_args, posix=os.name != "nt")
        if isinstance(extra_args, (list, tuple)):
            return [str(arg) for arg in extra_args]
        raise TypeError("command args must be str, list, or tuple")
