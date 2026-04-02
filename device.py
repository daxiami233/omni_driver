from automator import H2, U2, SwipeDirection
from connector import ADB, HDC
from model import Element
from loguru import logger


class Driver:
    BACKENDS = {
        "android": (ADB, U2),
        "adb": (ADB, U2),
        "harmony": (HDC, H2),
        "hdc": (HDC, H2),
    }
    def __init__(self, device_serial: str, operating_system: str | None = None):
        self.serial = device_serial
        self.operating_system = self._resolve_operating_system(device_serial, operating_system)
        logger.info("initialize driver: serial={}, backend={}", self.serial, self.operating_system)
        try:
            connector_cls, automator_cls = self.BACKENDS[self.operating_system]
        except KeyError as exc:
            logger.error("unsupported operating system: {}", self.operating_system)
            raise ValueError(f"unsupported operating system: {self.operating_system}") from exc
        self.connector = connector_cls(self)
        self.automator = automator_cls(self)

    def install_app(self, app_path: str):
        return self.automator.install_app(app_path)

    def uninstall_app(self, package_name: str):
        return self.automator.uninstall_app(package_name)

    def start_app(self, package_name: str):
        return self.automator.start_app(package_name)

    def stop_app(self, package_name: str):
        return self.automator.stop_app(package_name)

    def restart_app(self, package_name: str):
        return self.automator.restart_app(package_name)

    def clear_app(self, package_name: str):
        return self.automator.clear_app(package_name)

    def click(self, x, y=None):
        if isinstance(x, Element):
            x, y = self._center_of(x)
        if y is None:
            raise ValueError("y is required when click target is coordinates")
        return self.automator.click(x, y)

    def long_click(self, x, y=None):
        if isinstance(x, Element):
            x, y = self._center_of(x)
        if y is None:
            raise ValueError("y is required when long_click target is coordinates")
        return self.automator.long_click(x, y)

    def swipe(self, x1, y1, x2, y2, duration=0.5):
        return self.automator.swipe(x1, y1, x2, y2, duration)

    def swipe_ext(self, direction: SwipeDirection | str, scale=0.4):
        return self.automator.swipe_ext(direction, scale)

    def input(self, value, arg2=None, arg3=None):
        # Support three forms: input(text), input(element, text), input(x, y, text).
        if isinstance(value, Element):
            if arg2 is None:
                raise ValueError("text is required when input target is an element")
            return self.automator.input(arg2, node=value)
        if isinstance(value, (int, float)) and isinstance(arg2, (int, float)):
            if arg3 is None:
                raise ValueError("text is required when input target is coordinates")
            return self.automator.input(arg3, x=value, y=arg2)
        if value is None:
            raise ValueError("text is required")
        return self.automator.input(value)

    def dump_hierarchy(self):
        return self.automator.dump_hierarchy()

    def get_elements(self, **kwargs):
        return self.dump_hierarchy()(**kwargs)

    def get_element(self, **kwargs):
        elements = self.get_elements(**kwargs)
        return elements[0] if elements else None

    def screenshot(self, path=""):
        return self.automator.screenshot(path)

    def home(self):
        return self.automator.home()

    def back(self):
        return self.automator.back()

    def recent(self):
        return self.automator.recent()

    def screen_on(self):
        return self.automator.screen_on()

    def screen_off(self):
        return self.automator.screen_off()

    @staticmethod
    def _center_of(element: Element):
        return element.attribute["center"]

    @classmethod
    def _resolve_operating_system(cls, device_serial: str, operating_system: str | None):
        if operating_system:
            logger.debug("use explicit backend {} for {}", operating_system, device_serial)
            return operating_system.lower()

        try:
            adb_devices = ADB.devices()
        except Exception:
            adb_devices = []

        try:
            hdc_devices = HDC.devices()
        except Exception:
            hdc_devices = []

        in_adb = device_serial in adb_devices
        in_hdc = device_serial in hdc_devices
        logger.debug(
            "resolve backend for {}: in_adb={}, in_hdc={}",
            device_serial,
            in_adb,
            in_hdc,
        )

        if in_adb and in_hdc:
            logger.error("device {} exists in both adb and hdc device lists", device_serial)
            raise ValueError(f"device_serial exists in both adb and hdc lists: {device_serial}")
        if in_adb:
            return "adb"
        if in_hdc:
            return "hdc"
        logger.error("cannot infer backend from device_serial={}", device_serial)
        raise ValueError(f"cannot infer operating system from device_serial: {device_serial}")
