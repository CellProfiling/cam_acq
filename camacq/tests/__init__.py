"""Test package."""
import threading

from test_server import EchoRequestHandler, EchoServer

IP = 'localhost'
PORT = 8895
# Create the test server
SERVER = EchoServer((IP, PORT), EchoRequestHandler)


def setup():
    """Set up test server."""
    # Start new thread for server
    thread = threading.Thread(target=SERVER.serve_forever)
    thread.start()


def teardown():
    """Shutdown test server."""
    SERVER.shutdown()
    SERVER.server_close()
