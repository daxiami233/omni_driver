from omni_driver.device import Driver
from omni_driver.model import Element


class _FakeAutomator:
    def __init__(self):
        self.calls = []

    def install_app(self, app_path):
        self.calls.append(("install_app", app_path))
        return "installed"

    def uninstall_app(self, package_name):
        self.calls.append(("uninstall_app", package_name))
        return "uninstalled"

    def clear_app(self, package_name):
        self.calls.append(("clear_app", package_name))
        return "cleared"

    def start_app(self, package_name):
        self.calls.append(("start_app", package_name))

    def stop_app(self, package_name):
        self.calls.append(("stop_app", package_name))

    def restart_app(self, package_name):
        self.calls.append(("restart_app", package_name))

    def click(self, x, y):
        self.calls.append(("click", x, y))

    def long_click(self, x, y):
        self.calls.append(("long_click", x, y))

    def input(self, text, x=None, y=None, node=None):
        self.calls.append(("input", text, x, y, node))

    def dump_hierarchy(self):
        self.calls.append(("dump_hierarchy",))
        return _FakeControlTree()

    def current_activity(self):
        return "MainActivity"

    def current_package(self):
        return "com.example.app"

    def screenshot(self, path=""):
        self.calls.append(("screenshot", path))
        return "image"

    def display_size(self):
        return 1080, 2340

    def home(self):
        self.calls.append(("home",))

    def back(self):
        self.calls.append(("back",))

    def recent(self):
        self.calls.append(("recent",))

    def screen_on(self):
        self.calls.append(("screen_on",))

    def screen_off(self):
        self.calls.append(("screen_off",))


class _FakeControlTree:
    def __call__(self, **kwargs):
        return [Element(attributes={"text": "hello"})]


class _FakeConnector:
    def __init__(self, shell_output=""):
        self.shell_output = shell_output
        self.calls = []

    def shell(self, args):
        self.calls.append(args)
        return self.shell_output


def _driver_without_connection():
    driver = object.__new__(Driver)
    driver.serial = "emulator-5554"
    driver.operating_system = "adb"
    driver.automator = _FakeAutomator()
    driver.connector = _FakeConnector()
    return driver


def test_lifecycle_methods_delegate_to_automator():
    driver = _driver_without_connection()

    assert driver.install_app("/tmp/app.apk") == "installed"
    assert driver.uninstall_app("com.example.app") == "uninstalled"
    assert driver.clear_app("com.example.app") == "cleared"

    driver.start_app("com.example.app")
    driver.stop_app("com.example.app")
    driver.restart_app("com.example.app")

    assert driver.automator.calls == [
        ("install_app", "/tmp/app.apk"),
        ("uninstall_app", "com.example.app"),
        ("clear_app", "com.example.app"),
        ("start_app", "com.example.app"),
        ("stop_app", "com.example.app"),
        ("restart_app", "com.example.app"),
    ]


def test_click_supports_element_target():
    driver = _driver_without_connection()
    element = Element(attributes={"center": (540, 1200)})

    driver.click(element)

    assert driver.automator.calls == [("click", 540, 1200)]


def test_click_requires_y_for_coordinates():
    import pytest

    driver = _driver_without_connection()

    with pytest.raises(ValueError):
        driver.click(100)


def test_input_supports_element_coordinate_and_text_forms():
    driver = _driver_without_connection()
    element = Element(attributes={"center": (540, 1200), "id": "input-box"})

    driver.input(element, "hello")
    driver.input(540, 1200, "hello")
    driver.input("hello")

    assert driver.automator.calls == [
        ("input", "hello", None, None, element),
        ("input", "hello", 540, 1200, None),
        ("input", "hello", None, None, None),
    ]


def test_get_element_returns_first_match():
    driver = _driver_without_connection()

    element = driver.get_element(text="hello")

    assert element.attribute["text"] == "hello"


def test_current_activity_and_package_delegate():
    driver = _driver_without_connection()

    assert driver.current_activity() == "MainActivity"
    assert driver.current_package() == "com.example.app"


def test_current_package_falls_back_to_dumpsys():
    driver = _driver_without_connection()
    driver.automator.current_package = lambda: ""
    driver.connector = _FakeConnector(
        shell_output="ACTIVITY com.fallback.app/.MainActivity ...\n"
    )

    assert driver.current_package() == "com.fallback.app"
    assert driver.connector.calls == ["dumpsys activity top"]


def test_display_size_and_key_presses_delegate():
    driver = _driver_without_connection()

    assert driver.display_size() == (1080, 2340)

    driver.home()
    driver.back()
    driver.recent()
    driver.screen_on()
    driver.screen_off()

    assert driver.automator.calls == [
        ("home",),
        ("back",),
        ("recent",),
        ("screen_on",),
        ("screen_off",),
    ]
