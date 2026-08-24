from types import SimpleNamespace

import numpy as np
import pytest

from omni_driver.automator.u2 import U2
from omni_driver.errors import DeviceOperationError, ScreenshotError
from omni_driver.model import Element


class _Target:
    def __init__(self, error=None):
        self.error = error
        self.values = []

    def set_text(self, value):
        if self.error:
            raise self.error
        self.values.append(value)
        return True


class _Driver:
    def __init__(self, target=None):
        self.target = target or _Target()
        self.selectors = []
        self.clicks = []
        self.keys = []

    def __call__(self, **selector):
        self.selectors.append(selector)
        return self.target

    def click(self, x, y):
        self.clicks.append((x, y))

    def send_keys(self, text, clear):
        self.keys.append((text, clear))
        return True


def _u2(driver=None):
    automator = object.__new__(U2)
    automator._serial = "emulator-5554"
    automator._driver = driver or _Driver()
    automator.device = SimpleNamespace(connector=None)
    return automator


def test_node_input_prefers_resource_id_only():
    driver = _Driver()
    automator = _u2(driver)
    node = Element(
        attributes={
            "id": "com.example:id/input",
            "type": "android.widget.EditText",
            "text": "",
            "center": [100, 200],
        }
    )

    automator.input("hello", node=node)

    assert driver.selectors == [{"resourceId": "com.example:id/input"}]
    assert driver.target.values == ["hello"]
    assert driver.clicks == []


def test_node_input_clicks_center_before_focused_fallback():
    driver = _Driver(target=_Target(RuntimeError("stale selector")))
    automator = _u2(driver)
    node = Element(attributes={"id": "input", "center": [100, 200]})

    automator.input("hello", node=node)

    assert driver.clicks == [(100, 200)]
    assert driver.keys == [("hello", True)]


def test_screenshot_creates_parent_and_writes_image(tmp_path, monkeypatch):
    automator = _u2()
    image = np.zeros((20, 10, 3), dtype=np.uint8)
    monkeypatch.setattr(automator, "_adb_screenshot", lambda: image)
    output = tmp_path / "nested" / "screen.png"

    assert automator.screenshot(output) is image
    assert output.is_file()


def test_screenshot_rejects_empty_fallback(monkeypatch):
    automator = _u2()
    monkeypatch.setattr(automator, "_adb_screenshot", lambda: None)
    automator._driver.screenshot = lambda **_kwargs: None

    with pytest.raises(ScreenshotError, match="empty"):
        automator.screenshot()


def test_device_operation_errors_include_action_and_serial():
    automator = _u2()
    automator._driver.click = lambda *_args: (_ for _ in ()).throw(RuntimeError("lost"))

    with pytest.raises(DeviceOperationError, match="Android click failed.*emulator-5554"):
        automator.click(100, 200)
