import threading

from nose.tools import *

from test_server import EchoRequestHandler, EchoServer

IP = 'localhost'
PORT = 8895
_address = (IP, PORT)
# Create the test server
SERVER = EchoServer(_address, EchoRequestHandler)


def setup():
    # Start new thread for server
    t = threading.Thread(target=SERVER.serve_forever)
    t.start()
    return


def teardown():
    SERVER.shutdown()
    SERVER.server_close()
    return
