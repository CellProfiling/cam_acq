"""Test socket client."""
import logging

from matrixscreener.cam import CAM, tuples_as_dict

_LOGGER = logging.getLogger(__name__)

# From https://github.com/arve0/matrixscreener/blob/master/tests/test_cam.py


class EchoSocket(object):
    """Dummy echo socket for mocking."""

    msg = ''

    def send(self, msg):
        """Send message."""
        self.msg = msg
        return len(msg)

    def recv(self, buffer_size):
        """Receive message."""
        return self.msg[0:buffer_size]

    def connect(self, where):
        """Connect socket."""
        pass

    def settimeout(self, timeout):
        """Set timeout."""
        pass

    def fileno(self):
        """Return mock representation of file descriptor."""
        # pylint: disable=no-self-use
        return 0


def test_client(monkeypatch):
    """Test socket client."""
    # mock socket
    monkeypatch.setattr("socket.socket", EchoSocket)
    # Create the client
    _LOGGER.debug('creating socket')
    cam = CAM()

    # monkeypatched EchoSocket will never flush
    def flush():
        """Flush socket."""
        pass
    cam.flush = flush

    # Send the data as a list of tuples.
    message = [('cmd', 'deletelist')]
    _LOGGER.debug('sending data: "%s"', message)
    response = cam.send(message)[0]

    _LOGGER.debug('response from server: "%s"', response)

    # Check that sent message and received response are the same, including
    # prefix.
    sent = tuples_as_dict(cam.prefix + message)
    assert sent == response

    _LOGGER.debug('done')
