from loguru import logger

from .automator import SwipeDirection
from .errors import (
    BackendUnavailableError,
    DeviceNotFoundError,
    DeviceOfflineError,
)
from .model import Element


def _load_android_backend():
    from .automator.u2 import U2
    from .connector.adb import ADB

    return ADB, U2


def _load_harmony_backend():
    from .automator.h2 import H2
    from .connector.hdc import HDC

    return HDC, H2


class Driver:
    BACKENDS = {
        "adb": _load_android_backend,
        "hdc": _load_harmony_backend,
    }
    BACKEND_ALIASES = {"android": "adb", "harmony": "hdc"}
    BACKEND_CAPABILITIES = {
        "adb": frozenset(
            {
                "app_management",
                "foreground_app",
                "hierarchy",
                "input",
                "screenshot",
                "screen_control",
            }
        ),
        "hdc": frozenset(
            {
                "app_management",
                "foreground_app",
                "hierarchy",
                "input",
                "screenshot",
                "screen_control",
            }
        ),
    }

    def __init__(self, device_serial: str, operating_system: str | None = None):
        self.serial = str(device_serial or "").strip()
        if not self.serial:
            raise ValueError("device_serial is required")
        self.operating_system = self._resolve_operating_system(self.serial, operating_system)
        logger.info("initialize driver: serial={}, backend={}", self.serial, self.operating_system)
        try:
            connector_cls, automator_cls = self.BACKENDS[self.operating_system]()
        except ImportError as exc:
            raise BackendUnavailableError(
                f"backend {self.operating_system!r} dependencies are unavailable: {exc}"
            ) from exc
        self.connector = connector_cls(self)
        self.automator = automator_cls(self)

    @classmethod
    def register_backend(
        cls,
        name: str,
        connector_cls,
        automator_cls,
        *,
        aliases=(),
        capabilities=(),
    ):
        """Register an additional backend without changing Driver call sites."""
        backend_name = str(name or "").strip().lower()
        if not backend_name:
            raise ValueError("backend name is required")
        cls.BACKENDS[backend_name] = lambda: (connector_cls, automator_cls)
        cls.BACKEND_CAPABILITIES[backend_name] = frozenset(capabilities)
        for alias in aliases:
            normalized_alias = str(alias or "").strip().lower()
            if normalized_alias:
                cls.BACKEND_ALIASES[normalized_alias] = backend_name

    def supports(self, capability: str) -> bool:
        return capability in self.BACKEND_CAPABILITIES.get(self.operating_system, ())

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

    def current_activity(self):
        current_activity = getattr(self.automator, "current_activity", None)
        if callable(current_activity):
            return current_activity()
        return ""

    def current_package(self):
        current_package = getattr(self.automator, "current_package", None)
        if callable(current_package):
            try:
                package = current_package()
                if package:
                    return package
            except Exception:
                pass

        if self.operating_system == "adb":
            try:
                output = self.connector.shell("dumpsys activity top")
                for line in output.splitlines():
                    line = line.strip()
                    if "ACTIVITY " not in line:
                        continue
                    activity_part = line.split("ACTIVITY ", 1)[1].split()[0]
                    if "/" in activity_part:
                        return activity_part.split("/", 1)[0]
                    return activity_part
            except Exception as exc:
                logger.warning("failed to resolve current Android package: {}", exc)
        return ""

    def screenshot(self, path=""):
        return self.automator.screenshot(path)

    def display_size(self):
        return self.automator.display_size()

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
        center = element.attribute.get("center")
        if not isinstance(center, (list, tuple)) or len(center) != 2:
            raise ValueError("element has no valid center coordinate")
        return center[0], center[1]

    @classmethod
    def _resolve_operating_system(cls, device_serial: str, operating_system: str | None):
        if operating_system:
            requested = str(operating_system).strip().lower()
            backend = cls.BACKEND_ALIASES.get(requested, requested)
            if backend not in cls.BACKENDS:
                raise BackendUnavailableError(f"unsupported backend: {operating_system}")
            logger.debug("use explicit backend {} for {}", backend, device_serial)
            return backend

        detection_errors = []
        try:
            from .connector.adb import ADB

            adb_states = ADB.device_states()
            adb_state = adb_states.get(device_serial)
            if adb_state == "device":
                return "adb"
            if adb_state:
                raise DeviceOfflineError(
                    f"Android device {device_serial!r} is not ready: {adb_state}"
                )
        except DeviceOfflineError:
            raise
        except Exception as exc:
            detection_errors.append(f"adb: {exc}")

        try:
            from .connector.hdc import HDC

            hdc_devices = HDC.devices()
            if device_serial in hdc_devices:
                return "hdc"
        except Exception as exc:
            detection_errors.append(f"hdc: {exc}")

        detail = f" ({'; '.join(detection_errors)})" if detection_errors else ""
        raise DeviceNotFoundError(
            f"cannot find a ready device with serial {device_serial!r}{detail}"
        )
