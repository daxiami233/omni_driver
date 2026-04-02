import logging
import os
import shutil
import uuid

import cv2
from hmdriver2.driver import Driver
from hmdriver2.proto import KeyCode
from loguru import logger

from model.control_tree import ControlTreeParser

from .base import Automator

h2_logger = logging.getLogger("hmdriver2")
h2_logger.setLevel(logging.CRITICAL)


class H2(Automator):
    def __init__(self, device):
        super().__init__(device)
        self._serial = device.serial
        self._driver = Driver(self._serial)
        logger.debug("hmdriver2 connected: {}", self._serial)

    def install_app(self, app_path: str):
        logger.info("h2 install app: {}", app_path)
        return self._driver.install_app(app_path)

    def uninstall_app(self, package_name: str):
        logger.info("h2 uninstall app: {}", package_name)
        return self._driver.uninstall_app(package_name)

    def start_app(self, package_name: str):
        logger.info("h2 start app: {}", package_name)
        return self._driver.start_app(package_name)

    def stop_app(self, package_name: str):
        logger.info("h2 stop app: {}", package_name)
        return self._driver.stop_app(package_name)

    def clear_app(self, package_name: str):
        logger.info("h2 clear app: {}", package_name)
        return self._driver.clear_app(package_name)

    def click(self, x, y):
        return self._driver.click(x, y)

    def long_click(self, x, y):
        return self._driver.long_click(x, y)

    def swipe(self, x1, y1, x2, y2, duration=0.5):
        speed = self._duration_to_speed(x1, y1, x2, y2, duration)
        return self._driver.swipe(x1, y1, x2, y2, speed)

    def input(self, text, x=None, y=None, node=None):
        if node is not None:
            node_id = node.attribute.get("id", "")
            if not node_id:
                logger.error("h2 input failed: target node has no id")
                raise ValueError("target node has no id")
            logger.debug("h2 input via node: id={}, text={}", node_id, text)
            return self._driver(id=node_id).input_text(text)
        if x is not None and y is not None:
            logger.debug("h2 input via coordinates: ({}, {})", x, y)
            self.click(x, y)
        logger.debug("h2 input via focused control: {}", text)
        return self._driver.input_text(text)

    def dump_hierarchy(self):
        return ControlTreeParser.parse_hdc_json(self._driver.dump_hierarchy())

    def screenshot(self, path=""):
        temp_path = f"_tmp_{uuid.uuid4().hex}.jpeg"
        try:
            local_path = self._driver.screenshot(temp_path)
            image = cv2.imread(local_path)
            if path:
                logger.debug("h2 save screenshot: {}", path)
                shutil.copyfile(local_path, path)
            return image
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def home(self):
        return self._driver.go_home()

    def back(self):
        return self._driver.go_back()

    def recent(self):
        return self._driver.press_key(KeyCode.TASKMANAGER)

    def screen_on(self):
        return self._driver.screen_on()

    def screen_off(self):
        return self._driver.screen_off()

    def _duration_to_speed(self, x1, y1, x2, y2, duration):
        if duration is None or duration <= 0:
            return 2000

        width, height = self._driver.display_size
        start_x = x1 * width if 0 <= x1 <= 1 else x1
        start_y = y1 * height if 0 <= y1 <= 1 else y1
        end_x = x2 * width if 0 <= x2 <= 1 else x2
        end_y = y2 * height if 0 <= y2 <= 1 else y2
        distance = ((end_x - start_x) ** 2 + (end_y - start_y) ** 2) ** 0.5

        speed = int(distance / duration)
        return min(max(speed, 200), 40000)
