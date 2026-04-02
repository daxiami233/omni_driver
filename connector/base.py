import subprocess
from abc import ABC, abstractmethod
from loguru import logger


class Connector(ABC):
    def __init__(self, device=None):
        self.device = device

    @abstractmethod
    def run_cmd(self, extra_args):
        pass

    @abstractmethod
    def shell(self, extra_args):
        pass

    def _check_output(self, args):
        logger.debug("run command: {}", args)
        result = subprocess.check_output(args).strip()
        if not isinstance(result, str):
            result = result.decode()
        logger.debug("command output: {}", result)
        return result
