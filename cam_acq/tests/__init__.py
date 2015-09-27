import threading
from nose.tools import *
from test_server import EchoServer
from test_server import EchoRequestHandler

IP = 'localhost'
PORT = 8895
_address = (IP, PORT)
# Create the test server
SERVER = EchoServer(_address, EchoRequestHandler)


def setup():
    # Start new thread for server
    t = threading.Thread(target=SERVER.serve_forever)
    t.setDaemon(True)  # don't hang on exit
    t.start()
    return


def teardown():
    SERVER.socket.close()
    SERVER.server_close()
    return
