import subprocess
from loguru import logger

from .base import Connector


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
        return self.run_cmd(f"shell {extra_args}")

    @classmethod
    def devices(cls):
        result = subprocess.check_output(["hdc", "list", "targets"]).strip()
        if not isinstance(result, str):
            result = result.decode()
        devices = result.splitlines()
        logger.debug("hdc devices: {}", devices)
        return devices

    @staticmethod
    def _normalize_args(extra_args):
        if isinstance(extra_args, str):
            return extra_args.split()
        if isinstance(extra_args, list):
            return extra_args
        raise TypeError("command args must be str or list")
