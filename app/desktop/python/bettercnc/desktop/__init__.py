"""Public desktop composition; LinuxCNC and preview stay behind their APIs."""

__all__ = ["DesktopBackend", "main"]


def main(argv=None):
    from ._application import main as run

    return run(argv)


def __getattr__(name):
    if name == "DesktopBackend":
        from ._backend import DesktopBackend

        return DesktopBackend
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
