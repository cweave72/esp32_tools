import logging

from protorpc.api import Api, FrameDict, parse_fields

logger = logging.getLogger(__name__)


def build_api(frame_cls, conn):

    api = {}
    parse_fields(frame_cls())
    logger.debug(f"FrameDict={FrameDict}")

    for callset in FrameDict:
        logger.debug(f"Building api for callset {callset}")
        api[callset] = Api(frame_cls, FrameDict[callset], conn)

    return api
