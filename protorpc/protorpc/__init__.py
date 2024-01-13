import logging
from rich.logging import RichHandler
from rich.console import Console

from protorpc.api import Api, FrameDict, parse_fields

logger = logging.getLogger(__name__)

loglevels = {
    "error": logging.ERROR,
    "warning": logging.WARNING,
    "info": logging.INFO,
    "debug": logging.DEBUG,
}

fmt_str = "[%(levelname)6s] (%(filename)s:%(lineno)s) %(message)s"


def setup_logging(rootlogger, level, logfile=None):

    rootlogger.setLevel(logging.DEBUG)

    if logfile:
        fh = logging.FileHandler(logfile, mode='w')
        fmt = logging.Formatter(fmt=fmt_str)

        fh.setFormatter(fmt)
        fh.setLevel(logging.DEBUG)
        rootlogger.addHandler(fh)

    con = Console()
    if con.is_terminal:
        ch = RichHandler(rich_tracebacks=True, show_time=False)
    else:
        ch = logging.StreamHandler()
        fmt = logging.Formatter(fmt=fmt_str)
        ch.setFormatter(fmt)

    ch.setLevel(loglevels[level])
    rootlogger.addHandler(ch)


def build_api(frame_cls, conn):

    api = {}
    parse_fields(frame_cls())
    logger.debug(f"FrameDict={FrameDict}")

    for callset in FrameDict:
        logger.debug(f"Building api for callset: '{callset}'")
        api[callset] = Api(frame_cls, FrameDict[callset], conn)

    return api
