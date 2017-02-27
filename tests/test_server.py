"""Handle test server."""
# Python socket server example taken from pymotw

import logging
import SocketServer
# import threading

logging.basicConfig(level=logging.DEBUG, format='%(name)s: %(message)s')

_LOGGER = logging.getLogger(__name__)


class EchoRequestHandler(SocketServer.BaseRequestHandler):
    """Request handler of test server."""

    def __init__(self, request, client_address, server):
        """Set up instance attributes."""
        self.logger = logging.getLogger('EchoRequestHandler')
        self.logger.debug('__init__')
        SocketServer.BaseRequestHandler.__init__(
            self, request, client_address, server)

    def setup(self):
        """Set up handler."""
        self.logger.debug('setup')
        self.request.send('Welcome')
        return SocketServer.BaseRequestHandler.setup(self)

    def handle(self):
        """Handle requests."""
        self.logger.debug('handle')

        # Echo the back to the client
        data = self.request.recv(1024)
        self.logger.debug('recv()->"%s"', data)
        self.request.send(data)

    def finish(self):
        """Finish requests."""
        self.logger.debug('finish')
        return SocketServer.BaseRequestHandler.finish(self)


class EchoServer(SocketServer.TCPServer):
    """Test server."""

    def __init__(self, server_address, handler_class=EchoRequestHandler):
        """Set up instance attributes."""
        self.logger = logging.getLogger('EchoServer')
        self.logger.debug('__init__')
        SocketServer.TCPServer.allow_reuse_address = True
        SocketServer.TCPServer.__init__(self, server_address, handler_class)


if __name__ == '__main__':

    ADDRESS = ('localhost', 8895)
    SERVER = EchoServer(ADDRESS, EchoRequestHandler)
    # ip, port = server.server_address  # find out what port we were given

    # THREAD = threading.Thread(target=SERVER.serve_forever)
    # THREAD.start()
    try:
        _LOGGER.debug('Serve forever')
        SERVER.serve_forever()
    except KeyboardInterrupt:
        # Clean up
        _LOGGER.debug('Server shutdown')
        SERVER.shutdown()
        _LOGGER.debug('Server close')
        SERVER.server_close()
