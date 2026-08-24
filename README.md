# omni_driver

`omni_driver` is a source-copyable device automation driver. Android is the
currently verified backend; HarmonyOS code is retained but loaded only when
that backend is selected.

## Android setup

Install `adb` and ensure it is available on `PATH`, then install the Python
dependencies:

```bash
pip install loguru numpy opencv-python uiautomator2
python -m uiautomator2 -s <serial> init
```

Copy the complete `omni_driver` directory into a project and use only the
public `Driver` facade:

```python
from omni_driver import Driver

device = Driver("emulator-5554")
device.start_app("com.example.app")
image = device.screenshot()
device.click(0.5, 0.5)  # values in [0, 1] are screen ratios
device.input("hello")
device.back()
```

Frequently used APIs include application lifecycle operations, coordinate or
element interaction, UI hierarchy queries, foreground package/activity,
screenshots, display size, system keys, and `device.connector.shell(...)`.

Use an explicit backend when automatic device discovery is not desired:

```python
device = Driver("emulator-5554", operating_system="android")
```

All stable driver exceptions inherit from `omni_driver.DriverError`.
