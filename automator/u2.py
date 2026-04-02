import cv2
import uiautomator2
from loguru import logger

from model.control_tree import ControlTreeParser

from .base import Automator


class U2(Automator):
    def __init__(self, device):
        super().__init__(device)
        self._serial = device.serial
        self._driver = uiautomator2.connect(self._serial)
        logger.debug("uiautomator2 connected: {}", self._serial)

    def install_app(self, app_path: str):
        logger.info("u2 install app: {}", app_path)
        return self._driver.app_install(app_path)

    def uninstall_app(self, package_name: str):
        logger.info("u2 uninstall app: {}", package_name)
        return self._driver.app_uninstall(package_name)

    def start_app(self, package_name: str):
        logger.info("u2 start app: {}", package_name)
        return self._driver.app_start(package_name)

    def stop_app(self, package_name: str):
        logger.info("u2 stop app: {}", package_name)
        return self._driver.app_stop(package_name)

    def clear_app(self, package_name: str):
        logger.info("u2 clear app: {}", package_name)
        return self._driver.app_clear(package_name)

    def click(self, x, y):
        px, py = self._normalize_point(x, y)
        return self._driver.click(px, py)

    def long_click(self, x, y):
        px, py = self._normalize_point(x, y)
        return self._driver.long_click(px, py, 1.5)

    def swipe(self, x1, y1, x2, y2, duration=0.5):
        sx, sy = self._normalize_point(x1, y1)
        ex, ey = self._normalize_point(x2, y2)
        return self._driver.swipe(sx, sy, ex, ey, duration)

    def input(self, text, x=None, y=None, node=None):
        if node is not None:
            node_id = node.attribute.get("id", "")
            node_type = node.attribute.get("type", "")
            node_text = node.attribute.get("text", "")
            target = self._driver(
                resourceId=node_id,
                className=node_type,
                text=node_text,
                enabled="true",
            )
            try:
                logger.debug("u2 input via node: id={}, type={}, text={}", node_id, node_type, text)
                return target.set_text(text)
            except Exception as exc:
                logger.warning("u2 node input failed, fallback to focused input: {}", exc)
        if x is not None and y is not None:
            logger.debug("u2 input via coordinates: ({}, {})", x, y)
            self.click(x, y)
        logger.debug("u2 input via focused control: {}", text)
        return self._driver.send_keys(text, True)

    def dump_hierarchy(self):
        return ControlTreeParser.parse_adb_xml(self._driver.dump_hierarchy(compressed=False))

    def screenshot(self, path=""):
        image = self._driver.screenshot(format="opencv")
        if path:
            logger.debug("u2 save screenshot: {}", path)
            cv2.imwrite(path, image)
        return image

    def home(self):
        return self._driver.press("home")

    def back(self):
        return self._driver.press("back")

    def recent(self):
        return self._driver.press("recent")

    def screen_on(self):
        return self._driver.screen_on()

    def screen_off(self):
        return self._driver.screen_off()

    def _normalize_point(self, x, y):
        if 0 <= x <= 1 and 0 <= y <= 1:
            info = self._driver.info
            return int(x * info["displayWidth"]), int(y * info["displayHeight"])
        return x, y
