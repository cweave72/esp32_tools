import time
import datetime
import logging
from threading import Thread, Event
from queue import Queue

logger = logging.getLogger(__name__)


class BaseConnection(Thread):
    """Base connection class.
    """

    def __init__(self, name, addr: str, port: int, *args, **kwargs):
        self.timeout = kwargs.pop('timeout', 2)
        super().__init__(*args, **kwargs)
        self.name = name
        self.seqn = 0

        self.addr = addr
        self.port = port

        self.pending_request = None
        self.event = Event()

        self.start()

    def get_next_seqn(self):
        """Iterates and returns the sequence number.
        """
        self.seqn += 1
        return self.seqn

    def stop(self):
        """Stops the connection service.
        """
        self.event.set()

    def close(self):
        """Close the connection.
        """
        self.stop()
        self.join()

    def add_pending(self, request):
        """Adds a request to the pending list.
        """
        self.pending_request = request

    #def remove_pending(self, seqn):
    #    """Removes a request to the pending list.
    #    """
    #    for r_seqn in self.pending_requests:
    #        if r_seqn == seqn:
    #            logger.debug(f"Removing seqn={seqn} from pending list.")
    #            self.pending_requests.pop(seqn)
    def remove_pending(self, seqn):
        self.pending_request = None

    def read_loop(self):
        """Read from port.  Must be implemented by subclass.
        """
        raise NotImplementedError

    def run(self):

        logger.debug("Starting thread loop.")

        while True:

            if self.event.is_set():
                logger.debug("Base thread stopping.")
                break

            if self.pending_request is not None:
                data = self.read_loop()

                if data is not None:
                    reply = self.pending_request.reply
                    try:
                        reply.rcv_handler(data)
                        if reply.seqn == self.pending_request.seqn:
                            logger.debug(f"Got reply for seqn={reply.seqn}")
                            self.pending_request.got_reply = True
                            self.remove_pending(reply.seqn)
                            continue
                    except Exception as e:
                        logger.error("Error receiving data, "
                                     "dropping request with "
                                     f"seqn={self.pending_request.seqn}: {str(e)}.")
                        self.remove_pending(0)
                        continue

                # Test for pending request timeout.
                if datetime.datetime.now() > self.pending_request.ttl:
                    logger.error("Removing request frame due to timeout: "
                                 f"{self.pending_request.frame}")
                    self.pending_request.timedout = True
                    self.remove_pending(0)

            time.sleep(0.1)
