import logging
from rich.logging import RichHandler

logger = logging.getLogger(__name__)

loglevels = {
    "error": logging.ERROR,
    "warning": logging.WARNING,
    "info": logging.INFO,
    "debug": logging.DEBUG,
}


def setup_logging(rootlogger, level, logfile=None):

    rootlogger.setLevel(logging.DEBUG)

    if logfile:
        fh = logging.FileHandler(logfile, mode='w')
        fmt = logging.Formatter(
            fmt="%(asctime)s: [%(levelname)6s] %(name)s: %(message)s")

        fh.setFormatter(fmt)
        fh.setLevel(logging.DEBUG)
        rootlogger.addHandler(fh)

    ch = RichHandler(rich_tracebacks=True, show_time=False)
    ch.setLevel(loglevels[level])
    rootlogger.addHandler(ch)
