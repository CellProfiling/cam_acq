"""Test socket client."""
import logging
from collections import OrderedDict

from matrixscreener.cam import CAM

IP = 'localhost'
PORT = 8895


def test_client():
    """Test socket client."""
    # Create the client
    logger = logging.getLogger('client')
    logger.info('Server on %s:%s', IP, PORT)
    logger.debug('creating socket')
    cam = CAM(IP)

    # Send the data as a list of tuples.
    message = [('cmd', 'deletelist')]
    logger.debug('sending data: "%s"', message)
    response = cam.send(message)

    logger.debug('response from server: "%s"', response)

    # Check that sent message and received response are the same, including
    # prefix.
    for cmd, val in response[0].iteritems():
        assert OrderedDict(cam.prefix + message)[cmd] == val

    # Clean up
    logger.debug('closing socket')
    cam.socket.close()
    logger.debug('done')
