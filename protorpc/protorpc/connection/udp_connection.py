import logging
import socket
import typing as t

from protorpc.connection import BaseConnection

logger = logging.getLogger(__name__)


class UdpConnection(BaseConnection):
    """A connection class using UDP.
    """

    def __init__(self, addr: str, port: int, **kwargs):
        super().__init__('udpconn', addr, port, **kwargs)
        self.is_connected = False

    def connect(self, timeout=1, rcvbuf_size=1024):
        self.rcv_timeout = timeout
        self.rcvbuf_size = rcvbuf_size
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.settimeout(self.rcv_timeout)
        self.is_connected = True
        logger.debug(f"UdpConnection connected {self.addr}:{self.port}")

    def write(self, data: t.ByteString) -> None:
        """Sends data.
        """
        logger.debug(f"Writing data[{len(data)}]={data} to {self.addr}:{self.port}")
        if self.is_connected:
            self.socket.sendto(data, (self.addr, self.port))
        else:
            logger.warning("Udp write: Not Connected.  Call connect() before write().")

    def close(self):
        """Closes the connection.
        """
        super().close()
        logger.debug("UdpConnection closing.")
        self.socket.close()

    def read_loop(self):
        """Reads the socket for data.
        """
        try:
            data, addr = self.socket.recvfrom(self.rcvbuf_size)
            if not data:
                return None

            logger.debug(f"Received data[{len(data)}]={data}")
            return data

        except socket.timeout:
            return None
        except Exception as e:
            logger.error(f"Udp read_loop: {str(e)}")
            return None
