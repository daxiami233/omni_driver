from .base import Automator as Automator, SwipeDirection as SwipeDirection

__all__ = ["Automator", "SwipeDirection", "H2", "U2"]


def __getattr__(name):
    # Platform adapters are optional until their backend is actually selected.
    if name == "U2":
        from .u2 import U2

        return U2
    if name == "H2":
        from .h2 import H2

        return H2
    raise AttributeError(name)
