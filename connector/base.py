import subprocess
from abc import ABC, abstractmethod

from loguru import logger

from .._config import positive_float_env
from ..errors import DeviceCommandError, DeviceCommandTimeoutError

DEFAULT_DEVICE_COMMAND_TIMEOUT = positive_float_env("DEVICE_COMMAND_TIMEOUT", 30)


class Connector(ABC):
    def __init__(self, device=None, command_timeout=None):
        self.device = device
        self.command_timeout = (
            DEFAULT_DEVICE_COMMAND_TIMEOUT
            if command_timeout is None
            else max(1.0, float(command_timeout))
        )

    @abstractmethod
    def run_cmd(self, extra_args):
        pass

    @abstractmethod
    def shell(self, extra_args):
        pass

    def _check_output(self, args):
        logger.debug("run command: {}", args)
        try:
            result = subprocess.check_output(
                args,
                timeout=self.command_timeout,
            ).strip()
        except subprocess.TimeoutExpired as exc:
            executable = str(args[0]) if args else "device command"
            logger.error(
                "device command timed out: executable={}, timeout={}s",
                executable,
                self.command_timeout,
            )
            raise DeviceCommandTimeoutError(
                f"{executable} command timed out after {self.command_timeout:g}s"
            ) from exc
        except FileNotFoundError as exc:
            executable = str(args[0]) if args else "device command"
            raise DeviceCommandError(f"required executable not found: {executable}") from exc
        except subprocess.CalledProcessError as exc:
            executable = str(args[0]) if args else "device command"
            stderr = getattr(exc, "stderr", None)
            if isinstance(stderr, bytes):
                stderr = stderr.decode(errors="replace")
            detail = str(stderr or getattr(exc, "output", None) or "").strip()
            message = f"{executable} command failed with exit code {exc.returncode}"
            if detail:
                message = f"{message}: {detail}"
            raise DeviceCommandError(message) from exc
        if not isinstance(result, str):
            result = result.decode(errors="replace")
        logger.debug("command output: {}", result)
        return result
