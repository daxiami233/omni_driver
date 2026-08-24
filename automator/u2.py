import re
import subprocess
from pathlib import Path

import cv2
import numpy as np
import uiautomator2
from loguru import logger

from .._config import positive_float_env
from ..errors import DeviceOperationError, DriverError, HierarchyError, ScreenshotError
from ..model.control_tree import ControlTreeParser
from .base import Automator


ADB_SCREENSHOT_TIMEOUT = positive_float_env("ADB_SCREENSHOT_TIMEOUT", 12)
ADB_WM_SIZE_TIMEOUT = positive_float_env("ADB_WM_SIZE_TIMEOUT", 5)
ADB_LAUNCHER_QUERY_TIMEOUT = positive_float_env("ADB_LAUNCHER_QUERY_TIMEOUT", 5)
WM_SIZE_PATTERN = re.compile(r"(?:Physical|Override) size:\s*(\d+)x(\d+)")
LAUNCHER_COMPONENT_PATTERN = re.compile(
    r"^\s*[A-Za-z0-9._]+/([A-Za-z0-9._$]+)\s*$",
    re.MULTILINE,
)


class U2(Automator):
    def __init__(self, device):
        super().__init__(device)
        self._serial = device.serial
        try:
            self._driver = uiautomator2.connect(self._serial)
        except Exception as exc:
            raise DeviceOperationError(
                f"failed to connect to Android device {self._serial!r}: {exc}"
            ) from exc
        logger.debug("uiautomator2 connected: {}", self._serial)

    def install_app(self, app_path: str):
        app_path = self._require_text(app_path, "app_path")
        logger.info("u2 install app: {}", app_path)
        return self._call_driver("install app", self._driver.app_install, app_path)

    def uninstall_app(self, package_name: str):
        package_name = self._require_text(package_name, "package_name")
        logger.info("u2 uninstall app: {}", package_name)
        return self._call_driver("uninstall app", self._driver.app_uninstall, package_name)

    def start_app(self, package_name: str):
        package_name = self._require_text(package_name, "package_name")
        logger.info("u2 start app: {}", package_name)
        activity = self._preferred_launcher_activity(package_name)
        if activity:
            logger.debug("u2 start app with launcher activity: {}", activity)
            return self._call_driver(
                "start app",
                self._driver.app_start,
                package_name,
                activity=activity,
            )
        return self._call_driver("start app", self._driver.app_start, package_name)

    def _preferred_launcher_activity(self, package_name: str) -> str:
        try:
            result = subprocess.run(
                [
                    "adb", "-s", self._serial, "shell", "cmd", "package",
                    "query-activities", "--brief", "-a", "android.intent.action.MAIN",
                    "-c", "android.intent.category.LAUNCHER", package_name,
                ],
                capture_output=True,
                text=True,
                timeout=ADB_LAUNCHER_QUERY_TIMEOUT,
                check=False,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            logger.warning("u2 failed to query launcher activity, using default start: {}", exc)
            return ""

        return_code = int(getattr(result, "returncode", 0) or 0)
        if return_code != 0:
            logger.warning(
                "u2 launcher query failed: package={}, code={}, stderr={}",
                package_name,
                return_code,
                (getattr(result, "stderr", "") or "").strip() or "unknown",
            )
            return ""

        activities = LAUNCHER_COMPONENT_PATTERN.findall(result.stdout or "")
        if not activities:
            return ""

        package_parts = package_name.split(".")

        def namespace_score(activity: str) -> int:
            activity_parts = activity.lstrip(".").split(".")
            return next(
                (index for index, pair in enumerate(zip(package_parts, activity_parts)) if pair[0] != pair[1]),
                min(len(package_parts), len(activity_parts)),
            )

        return max(activities, key=namespace_score)

    def stop_app(self, package_name: str):
        package_name = self._require_text(package_name, "package_name")
        logger.info("u2 stop app: {}", package_name)
        return self._call_driver("stop app", self._driver.app_stop, package_name)

    def clear_app(self, package_name: str):
        package_name = self._require_text(package_name, "package_name")
        logger.info("u2 clear app: {}", package_name)
        return self._call_driver("clear app", self._driver.app_clear, package_name)

    def click(self, x, y):
        px, py = self._normalize_point(x, y)
        return self._call_driver("click", self._driver.click, px, py)

    def long_click(self, x, y):
        px, py = self._normalize_point(x, y)
        return self._call_driver("long click", self._driver.long_click, px, py, 1.5)

    def swipe(self, x1, y1, x2, y2, duration=0.5):
        sx, sy = self._normalize_point(x1, y1)
        ex, ey = self._normalize_point(x2, y2)
        return self._call_driver("swipe", self._driver.swipe, sx, sy, ex, ey, duration)

    def input(self, text, x=None, y=None, node=None):
        if text is None:
            raise ValueError("text is required")
        text = str(text)
        if node is not None:
            selector = self._selector_for_node(node)
            if selector:
                try:
                    logger.debug("u2 input via node selector: {}", selector)
                    return self._driver(**selector).set_text(text)
                except Exception as exc:
                    logger.warning("u2 node input failed, fallback to focused input: {}", exc)
            center = node.attribute.get("center")
            if isinstance(center, (list, tuple)) and len(center) == 2:
                self.click(center[0], center[1])
        if x is not None and y is not None:
            logger.debug("u2 input via coordinates: ({}, {})", x, y)
            self.click(x, y)
        logger.debug("u2 input via focused control: {}", text)
        return self._call_driver("input text", self._driver.send_keys, text, True)

    def dump_hierarchy(self):
        try:
            source = self._driver.dump_hierarchy(compressed=False)
            return ControlTreeParser.parse_adb_xml(source)
        except HierarchyError:
            raise
        except Exception as exc:
            raise HierarchyError(f"failed to dump Android UI hierarchy: {exc}") from exc

    def current_activity(self):
        try:
            current = self._driver.app_current()
            if isinstance(current, dict):
                return current.get("activity", "") or ""
        except Exception as exc:
            logger.warning("u2 failed to get current activity, trying adb fallback: {}", exc)

        try:
            output = self.device.connector.shell("dumpsys activity top")
            for line in output.splitlines():
                line = line.strip()
                if "ACTIVITY " not in line:
                    continue
                activity_part = line.split("ACTIVITY ", 1)[1].split()[0]
                if "/" in activity_part:
                    return activity_part.split("/", 1)[1]
                return activity_part
        except Exception as exc:
            logger.warning("u2 adb fallback failed to get current activity: {}", exc)
        return ""

    def current_package(self):
        try:
            current = self._driver.app_current()
            if isinstance(current, dict):
                return current.get("package", "") or ""
        except Exception as exc:
            logger.warning("u2 failed to get current package, trying adb fallback: {}", exc)

        try:
            output = self.device.connector.shell("dumpsys activity top")
            for line in output.splitlines():
                line = line.strip()
                if "ACTIVITY " not in line:
                    continue
                activity_part = line.split("ACTIVITY ", 1)[1].split()[0]
                if "/" in activity_part:
                    return activity_part.split("/", 1)[0]
                return activity_part
        except Exception as exc:
            logger.warning("u2 adb fallback failed to get current package: {}", exc)
        return ""

    def screenshot(self, path=""):
        image = self._adb_screenshot()
        if image is None:
            try:
                image = self._driver.screenshot(format="opencv")
            except Exception as exc:
                raise ScreenshotError(f"failed to capture Android screenshot: {exc}") from exc
        if not isinstance(image, np.ndarray) or image.size == 0:
            raise ScreenshotError("Android screenshot is empty or has an unsupported format")
        if path:
            logger.debug("u2 save screenshot: {}", path)
            output_path = Path(path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                saved = cv2.imwrite(str(output_path), image)
            except Exception as exc:
                raise ScreenshotError(
                    f"failed to save Android screenshot {output_path}: {exc}"
                ) from exc
            if not saved:
                raise ScreenshotError(f"failed to save Android screenshot: {output_path}")
        return image

    def display_size(self):
        u2_error = None
        try:
            info = self._driver.info
            width = int(info["displayWidth"])
            height = int(info["displayHeight"])
            if width > 0 and height > 0:
                return width, height
            u2_error = ValueError(f"invalid uiautomator2 display size: {width}x{height}")
        except Exception as exc:
            u2_error = exc
            logger.warning("u2 failed to get display size, trying adb wm size fallback: {}", exc)

        wm_size = self._adb_wm_size()
        if wm_size is not None:
            return wm_size

        logger.warning("adb wm size fallback failed, trying adb screenshot size fallback")
        image = self._adb_screenshot()
        if image is not None and len(image.shape) >= 2:
            height, width = image.shape[:2]
            if width > 0 and height > 0:
                return int(width), int(height)

        raise RuntimeError(
            "failed to resolve display size: uiautomator2, adb wm size and screenshot fallbacks all failed"
        ) from u2_error

    def home(self):
        return self._call_driver("press home", self._driver.press, "home")

    def back(self):
        return self._call_driver("press back", self._driver.press, "back")

    def recent(self):
        return self._call_driver("press recent", self._driver.press, "recent")

    def screen_on(self):
        return self._call_driver("turn screen on", self._driver.screen_on)

    def screen_off(self):
        return self._call_driver("turn screen off", self._driver.screen_off)

    def _normalize_point(self, x, y):
        if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            raise TypeError("coordinates must be int or float")
        if 0 <= x <= 1 and 0 <= y <= 1:
            width, height = self.display_size()
            return int(x * width), int(y * height)
        return x, y

    def _adb_screenshot(self):
        cmd = ["adb", "-s", self._serial, "exec-out", "screencap", "-p"]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=ADB_SCREENSHOT_TIMEOUT,
                check=True,
            )
        except subprocess.TimeoutExpired:
            logger.warning("adb screenshot timed out: serial={}, timeout={}s", self._serial, ADB_SCREENSHOT_TIMEOUT)
            return None
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr.decode(errors="ignore").strip() if exc.stderr else ""
            logger.warning("adb screenshot failed: serial={}, stderr={}", self._serial, stderr or "unknown")
            return None
        except Exception as exc:
            logger.warning("adb screenshot error: serial={}, error={}", self._serial, exc)
            return None

        raw = result.stdout or b""
        if not raw:
            logger.warning("adb screenshot empty: serial={}", self._serial)
            return None

        image = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            logger.warning("adb screenshot decode failed: serial={}", self._serial)
        return image

    def _adb_wm_size(self):
        cmd = ["adb", "-s", self._serial, "shell", "wm", "size"]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=ADB_WM_SIZE_TIMEOUT,
                check=True,
            )
        except subprocess.TimeoutExpired:
            logger.warning("adb wm size timed out: serial={}, timeout={}s", self._serial, ADB_WM_SIZE_TIMEOUT)
            return None
        except subprocess.CalledProcessError as exc:
            stderr = (exc.stderr or "").strip()
            logger.warning("adb wm size failed: serial={}, stderr={}", self._serial, stderr or "unknown")
            return None
        except Exception as exc:
            logger.warning("adb wm size error: serial={}, error={}", self._serial, exc)
            return None

        matches = WM_SIZE_PATTERN.findall(result.stdout or "")
        if not matches:
            logger.warning("adb wm size output unparsable: serial={}, output={}", self._serial, (result.stdout or "").strip())
            return None
        width, height = matches[-1]
        return int(width), int(height)

    @staticmethod
    def _selector_for_node(node):
        attributes = node.attribute
        node_id = str(attributes.get("id") or "").strip()
        if node_id:
            return {"resourceId": node_id}

        selector = {}
        node_text = str(attributes.get("text") or "").strip()
        node_type = str(attributes.get("type") or "").strip()
        if node_text:
            selector["text"] = node_text
        if node_type:
            selector["className"] = node_type
        return selector

    @staticmethod
    def _require_text(value, name):
        normalized = str(value or "").strip()
        if not normalized:
            raise ValueError(f"{name} is required")
        return normalized

    def _call_driver(self, operation, callback, *args, **kwargs):
        try:
            return callback(*args, **kwargs)
        except DriverError:
            raise
        except Exception as exc:
            raise DeviceOperationError(
                f"Android {operation} failed on {self._serial!r}: {exc}"
            ) from exc
