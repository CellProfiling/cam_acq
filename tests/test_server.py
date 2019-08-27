"""Implement test server."""
import logging
import socket
from time import sleep

from leicacam.cam import tuples_as_bytes

CAM_REPLY = [
    [(
        'relpath',
        'subfolder/exp1/CAM1/slide--S00/chamber--U00--V00/field--X01--Y01'
        '/image--L0000--S00--U00--V00--J15--E04--O01'
        '--X01--Y01--T0000--Z00--C00.ome')],
    [(
        'relpath',
        'subfolder/exp1/CAM1/slide--S00/chamber--U00--V00/field--X02--Y02'
        '/image--L0000--S00--U00--V00--J15--E02--O01'
        '--X02--Y02--T0000--Z00--C31.ome')]]


def image_event(data):
    """Send a reply about saved image."""
    if 'startcamscan' in data.decode():
        return tuples_as_bytes(CAM_REPLY.pop())
    return None


class EchoServer:
    """Test server."""

    def __init__(self, server_address):
        """Set up server."""
        self.logger = logging.getLogger('EchoServer')
        self.logger.debug('Setting up server')
        self.server_address = server_address
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.setup()

    def setup(self):
        """Bind and listen to incoming connections."""
        self.sock.bind(self.server_address)
        self.sock.listen(1)

    def handle(self):
        """Handle incoming connections."""
        # pylint: disable=no-member
        self.logger.debug('Serve incoming connections')
        conn, addr = self.sock.accept()
        self.logger.debug('Connected by %s', addr)
        try:
            self.logger.debug('Send welcome')
            conn.sendall('Welcome...'.encode('utf-8'))
            while True:
                data = conn.recv(1024)
                if not data:
                    self.logger.debug('No data, closing')
                    break
                self.send(conn, data)
                reply = image_event(data)
                if not reply:
                    continue
                sleep(0.2)
                self.send(conn, reply)
        except OSError as exc:
            self.logger.error(exc)
        finally:
            self.logger.debug('Closing connection to %s', addr)
            conn.close()
            self.sock.shutdown(socket.SHUT_WR)
            self.sock.close()

    def send(self, conn, data):
        """Send data."""
        self.logger.debug('Sending: %s', data)
        conn.sendall(data + b'\n')

    def run(self):
        """Run server."""
        try:
            self.handle()
        except OSError as exc:
            self.logger.error('Error on socket: %s', exc)
            self.logger.debug('Server close')
            self.sock.close()

    def stop(self):
        """Stop server."""
        try:
            self.logger.debug('Server shutdown')
            self.sock.shutdown(socket.SHUT_WR)
            self.logger.debug('Server close')
            self.sock.close()
        except OSError:
            self.logger.error('Error shutting down server socket')


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(name)s: %(message)s')

    ADDRESS = ('localhost', 8895)
    SERVER = EchoServer(ADDRESS)

    try:
        SERVER.run()
    except KeyboardInterrupt:
        SERVER.stop()
