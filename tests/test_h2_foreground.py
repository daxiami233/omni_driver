from omni_driver.automator.h2 import H2


def test_h2_reads_foreground_package_and_ability_from_driver():
    automator = object.__new__(H2)

    class FakeDriver:
        def current_app(self):
            return "com.example.harmony", "EntryAbility"

    automator._driver = FakeDriver()

    assert automator.current_package() == "com.example.harmony"
    assert automator.current_activity() == "EntryAbility"


def test_h2_foreground_returns_empty_tuple_on_error():
    automator = object.__new__(H2)

    class FakeDriver:
        def current_app(self):
            raise RuntimeError("connection lost")

    automator._driver = FakeDriver()

    assert automator.current_package() == ""
    assert automator.current_activity() == ""


def test_h2_foreground_reads_dict_response():
    automator = object.__new__(H2)

    class FakeDriver:
        def current_app(self):
            return {"bundle_name": "com.example.harmony", "ability_name": "EntryAbility"}

    automator._driver = FakeDriver()

    assert automator.current_package() == "com.example.harmony"
    assert automator.current_activity() == "EntryAbility"
