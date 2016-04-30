# Python socket server example taken from pymotw

import logging
import SocketServer
import threading

logging.basicConfig(
    level=logging.DEBUG, format='%(name)s: %(message)s')


class EchoRequestHandler(SocketServer.BaseRequestHandler):

    def __init__(self, request, client_address, server):
        self.logger = logging.getLogger('EchoRequestHandler')
        self.logger.debug('__init__')
        SocketServer.BaseRequestHandler.__init__(
            self, request, client_address, server)

    def setup(self):
        self.logger.debug('setup')
        return SocketServer.BaseRequestHandler.setup(self)

    def handle(self):
        self.logger.debug('handle')

        # Echo the back to the client
        data = self.request.recv(1024)
        self.logger.debug('recv()->"%s"', data)
        self.request.send(data)

    def finish(self):
        self.logger.debug('finish')
        return SocketServer.BaseRequestHandler.finish(self)


class EchoServer(SocketServer.TCPServer):

    def __init__(self, server_address, handler_class=EchoRequestHandler):
        self.logger = logging.getLogger('EchoServer')
        self.logger.debug('__init__')
        SocketServer.TCPServer.allow_reuse_address = True
        SocketServer.TCPServer.__init__(self, server_address, handler_class)

if __name__ == '__main__':

    address = ('localhost', 8895)
    server = EchoServer(address, EchoRequestHandler)
    # ip, port = server.server_address  # find out what port we were given

    t = threading.Thread(target=server.serve_forever)
    t.start()

    # Clean up
    server.shutdown()
    server.server_close()
