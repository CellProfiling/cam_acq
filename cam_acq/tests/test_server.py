# Python socket server example taken from pymotw

import logging
import threading
import socket
from SocketServer import BaseRequestHandler, TCPServer

logging.basicConfig(
    level=logging.DEBUG, format='%(name)s: %(message)s')

class CamRequestHandler(BaseRequestHandler):
    def __init__(self, request, client_address, server):
        self.logger = logging.getLogger('CamRequestHandler')
        self.logger.debug('__init__')
        self.camlevel = 1
        BaseRequestHandler.__init__(self, request, client_address, server)
        return

    def setup(self):
        self.logger.debug('setup')
        return BaseRequestHandler.setup(self)

    def handle(self):
        self.logger.debug('handle')

        data = self.request.recv(1024)
        self.logger.debug('recv()->%s', data)
        self.request.send('test message')
        return

class CamTestServer(TCPServer):
    def __init__(self, server_address, handler_class=CamRequestHandler):
        self.logger = logging.getLogger('CamResponseServer')
        self.logger.debug('__init__')
        TCPServer.__init__(self, server_address, handler_class)
        return

    def server_activate(self):
        self.logger.debug('server_activate')
        TCPServer.server_activate(self)
        return

    def serve_forever(self):
        self.logger.debug('Waiting for a request')
        self.logger.info('Press <Ctrl-C> to quit handling requests')

        while True:
            self.handle_request()
        return

    def handle_request(self):
        self.logger.debug('handle request')
        return TCPServer.handle_request(self)

    def verify_request(self, request, client_address):
        self.logger.debug('verify_request(%s, %s)', request, client_address)
        return TCPServer.verify_request(self, request, client_address)

    def process_request(self, request, client_address):
        self.logger.debug('process_request(%s, %s)', request, client_address)
        return TCPServer.process_request(self, request, client_address)

    def server_close(self):
        self.logger.debug('server_close')
        return TCPServer.server_close(self)

    def finish_request(self, request, client_address):
        self.logger.debug('finish_request(%s, %s)', request, client_address)
        return TCPServer.finish_request(
            self, request, client_address)

    def close_request(self, request_address):
        self.logger.debug('close_request(%s)', request_address)
        return TCPServer.close_request(self, request_address)

if __name__ == '__main__':

    address = ('localhost', 8895)
    server = CamTestServer(address, CamRequestHandler)
    # ip, port = server.server_address  # find out what port we were given

    server.serve_forever()

    #Clean up
    server.socket.close()
    server.server_close()
