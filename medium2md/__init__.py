from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("medium2md-cli")
except PackageNotFoundError:  # running from a source tree without an install
    __version__ = "0.0.0+source"
