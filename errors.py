class DriverError(RuntimeError):
    """Base error raised by omni_driver."""


class BackendUnavailableError(DriverError):
    """Raised when a requested device backend cannot be loaded or detected."""


class DeviceNotFoundError(DriverError):
    """Raised when a serial cannot be found on any available backend."""


class DeviceOfflineError(DriverError):
    """Raised when a device is visible but not ready for commands."""


class DeviceOperationError(DriverError):
    """Raised when a device automation operation fails."""


class DeviceCommandError(DriverError):
    """Raised when a device CLI command fails."""


class DeviceCommandTimeoutError(DeviceCommandError, TimeoutError):
    """Raised when a device CLI command exceeds its hard timeout."""


class ScreenshotError(DriverError):
    """Raised when a screenshot cannot be captured, decoded, or saved."""


class HierarchyError(DriverError):
    """Raised when the current UI hierarchy cannot be parsed."""
