import sys
import time
import datetime
import logging
import typing as t

from dataclasses import dataclass, fields
from rich import inspect

logger = logging.getLogger(__name__)

FrameDict = {}


@dataclass
class MsgArg:
    name: str
    group: str
    proto_type: str
    number: int


@dataclass
class FrameMsg:
    name: str
    cls: t.Any
    args: t.List[MsgArg]


@dataclass
class FrameCallset:
    name: str
    cls: t.Any
    msgs: t.Dict


def get_field_metadata(field):
    """Helper function to extract field metadata from betterproto.
    """
    meta = field.metadata.get('betterproto')
    return dict(
        group=meta.group,
        proto_type=meta.proto_type,
        number=meta.number,
    )


def parse_fields(frame, callset_inst=None, msg_inst=None, debug=False):
    """Recursively process a protobuf frame, creating FrameDict global.
    """
    global FrameDict

    if debug:
        logger.debug(f"--> msg_inst={msg_inst}")

    for field in fields(frame):
        meta = get_field_metadata(field)

        if meta.get('proto_type') == 'message':
            field_cls = frame._cls_for(field)

            if meta.get('group') == 'callset':
                cs_inst = FrameCallset(name=field.name, cls=field_cls, msgs={})
                FrameDict[field.name] = cs_inst
                parse_fields(field_cls, cs_inst, None)
            elif meta.get('group') == 'msg':
                m_inst = FrameMsg(name=field.name, cls=field_cls, args=[])
                callset_inst.msgs[field.name] = m_inst
                parse_fields(field_cls, callset_inst, m_inst)
            else:
                m_inst = FrameMsg(name=field.name, cls=field_cls, args=[])
                parse_fields(field_cls, None, m_inst)

            continue

        if debug:
            logger.debug(f"Adding arg to {msg_inst.name}: {field.name}")

        kwargs = {**{'name': field.name}, **meta}
        msg_inst.args.append(MsgArg(**kwargs))


class Request:
    """RPC request class.
    """

    def __init__(
        self,
        frame_cls,
        conn,
        callset_name,
        callset_inst,
        msg_name,
        msg_inst,
        **kwargs
    ):
        self.no_reply = kwargs.pop('no_reply', False)
        self.conn = conn
        self.frame = frame_cls()
        self.callset = callset_inst
        self.header = self.frame.header
        self.reply = Reply(frame_cls, msg_name, msg_inst)
        self.got_reply = False
        self.timedout = False

        self.msg_name = msg_name
        self.msg_inst = msg_inst

        # Set message instance to the frame callset attribute.
        setattr(self.callset, msg_name, msg_inst)
        setattr(self.frame, callset_name, self.callset)

    def send(self, timeout=3):
        """Sends a serialized RPC frame using the underlying connection object.
        """
        self.header.seqn = self.conn.get_next_seqn()
        self.header.no_reply = self.no_reply
        ser = self.frame.SerializeToString()
        self.ttl = datetime.datetime.now() + datetime.timedelta(seconds=timeout)
        logger.debug(f"sending request: {self.frame}")
        self.conn.write(ser)

        if self.no_reply:
            return
        else:
            self.conn.add_pending(self)

    def send_sync(self, timeout=3):
        """Sends and waits for success or timeout.
        """
        self.send(timeout)

        if not self.no_reply:
            while True:
                time.sleep(0.1)
                if self.timedout:
                    self.reply.set_timedout()
                    return
                if self.got_reply:
                    return

    @property
    def seqn(self):
        """Gets the frame seqn.
        """
        return self.header.seqn


class Reply:
    """RPC reply class.
    """

    def __init__(self, frame_cls, call_msg_name, call_msg_inst):
        self.frame = frame_cls()
        # Save references to the call msg and instance.
        self.call_msg = call_msg_name
        self.call_msg_inst = call_msg_inst
        self.result = None
        self.success = False
        self.timedout = False

    def rcv_handler(self, data):
        """Parses raw received frame into class instance.
        """
        try:
            self.frame.parse(data)
            logger.debug(f"Decoded frame ({self.status_str}): {self.frame}")
            if self.status in [0, 3]:
                self.success = True
                self.result = self.get_reply_value()
        except Exception as e:
            logger.error(f"Error on frame parse: {str(e)}")
            raise e

    def get_reply_value(self):
        """Retrieves the message from the recieved frame based on which
        message was received.
        """
        which_callset = self.frame._group_current['callset']
        callset = getattr(self.frame, which_callset)
        logger.debug(f"reply: which_callset={which_callset}")
        which_msg = callset._group_current['msg']
        logger.debug(f"reply: which_msg={which_msg}")
        reply_value = getattr(callset, which_msg)
        return reply_value

    def set_timedout(self):
        self.timedout = True

    def exit_on_fail(self, on_exit_func=None):
        """Checks the return code and exits on failure.
        """
        if self.timedout or not self.success:
            logger.error(f"RPC error: {self.status_str}")
            if on_exit_func is not None:
                on_exit_func()
            sys.exit(1)

    @property
    def seqn(self):
        """Gets the reply frame seqn.
        """
        return self.frame.header.seqn

    @property
    def status(self):
        """Gets the reply status from the header.
        """
        return self.frame.header.status

    @property
    def status_str(self):
        if self.timedout:
            return "REQUEST TIMEOUT"

        status_str = {
            0: "SUCCESS",
            1: "BAD_RESOLVER_LOOKUP",
            2: "BAD_HANDLER_LOOKUP",
            3: "HANDLER_ERROR",
        }.get(self.status, 'UNDEFINED')
        return status_str


def call_factory(
    frame_cls,
    conn,
    callset_name: str,
    callset_cls: t.Any,
    msg_name: str,
    msg_cls: t.Any
):
    def call_func(*args, **kwargs):
        no_reply = kwargs.pop('no_reply', False)
        msg_inst = msg_cls(*args, **kwargs)
        req = Request(frame_cls,
                      conn,
                      callset_name,
                      callset_cls,
                      msg_name,
                      msg_inst,
                      no_reply=no_reply)
        req.send_sync()
        return req.reply
    call_func.__name__ = msg_name.rstrip('_call')
    return call_func


class Api:
    """RPC frame api class for a callset. Methods are callset functions.
    """

    def __init__(self, frame_cls, frame_callset: FrameCallset, conn) -> None:

        self.callset_name = frame_callset.name
        self.callset_inst = frame_callset.cls()
        self.conn = conn

        for msg, frame_msg in frame_callset.msgs.items():
            setattr(self, msg, frame_msg)

            if not msg.endswith('_call'):
                continue

            func = call_factory(frame_cls,
                                self.conn,
                                self.callset_name,
                                self.callset_inst,
                                msg,
                                frame_msg.cls)
            setattr(self, func.__name__, func)
