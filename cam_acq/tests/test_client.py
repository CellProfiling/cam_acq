# Python socket server example taken from pymotw

import socket
import logging
from nose.tools import *
from test_server import EchoServer
from test_server import EchoRequestHandler
from cam_acq.socket_client import Client


IP = 'localhost'
PORT = 8895


def test_client():
    # Create the client
    logger = logging.getLogger('client')
    logger.info('Server on %s:%s', IP, PORT)
    logger.debug('creating socket')
    s = Client()

    # Connect to the server
    logger.debug('connecting to server')
    s.connect(IP, PORT)

    # Send the data
    message = 'Hello, world\n'
    logger.debug('sending data: "%s"', message)
    s.send(message)

    # Receive a response
    #logger.debug('waiting for response')
    #response = s.recv_timeout(5, [message])
    #logger.debug('response from server: "%s"', response)

    # Check that sent message and received response are the same somehow?
    #assert_equal(message, response)

    # Clean up
    logger.debug('closing socket')
    s.close()
    logger.debug('done')
    return
