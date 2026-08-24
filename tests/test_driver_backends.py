from types import SimpleNamespace

import pytest

from omni_driver.device import Driver
from omni_driver.errors import BackendUnavailableError, DeviceOfflineError


def test_explicit_backend_alias_is_normalized():
    assert Driver._resolve_operating_system("serial", "android") == "adb"
    assert Driver._resolve_operating_system("serial", "harmony") == "hdc"


def test_unknown_explicit_backend_has_stable_error():
    with pytest.raises(BackendUnavailableError, match="unsupported backend"):
        Driver._resolve_operating_system("serial", "ios")


def test_offline_android_device_is_not_treated_as_connected(monkeypatch):
    monkeypatch.setattr(
        "omni_driver.connector.adb.ADB.device_states",
        lambda: {"serial": "offline"},
    )

    with pytest.raises(DeviceOfflineError, match="offline"):
        Driver._resolve_operating_system("serial", None)


def test_custom_backend_registration_and_capabilities():
    class Connector:
        def __init__(self, device):
            self.device = device

    class Automator:
        def __init__(self, device):
            self.device = device

    try:
        Driver.register_backend(
            "sample",
            Connector,
            Automator,
            aliases=("sample-os",),
            capabilities=("screenshot",),
        )
        driver = Driver("serial", "sample-os")

        assert isinstance(driver.connector, Connector)
        assert isinstance(driver.automator, Automator)
        assert driver.supports("screenshot") is True
        assert driver.supports("hierarchy") is False
    finally:
        Driver.BACKENDS.pop("sample", None)
        Driver.BACKEND_ALIASES.pop("sample-os", None)
        Driver.BACKEND_CAPABILITIES.pop("sample", None)


def test_harmony_current_package_does_not_use_android_dumpsys():
    driver = object.__new__(Driver)
    driver.operating_system = "hdc"
    driver.automator = SimpleNamespace(current_package=lambda: "")
    driver.connector = SimpleNamespace(
        shell=lambda _command: pytest.fail("Android fallback should not run")
    )

    assert driver.current_package() == ""
