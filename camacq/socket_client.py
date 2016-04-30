"""Handle socket client."""
import socket
import sys
import time


class Client(object):
    """Client class."""

    def __init__(self, sock=None):
        """Set up instance."""
        # Create a TCP/IP socket
        try:
            if sock is None:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            else:
                self.sock = sock
        except socket.error:
            print 'Failed to create socket'
            sys.exit()
        print 'Socket Created'

    def recv_timeout(self, timeout, test):
        """Receive reply from server.

        Use a timeout and a list of strings to test. When all test strings
        are received, the listening loop ends.

        Parameters
        ----------
        timeout : int
            A timeout.
        test : list
            A list of strings to test.
        """
        # make socket non blocking
        self.sock.setblocking(False)

        # total data in an array
        total_data = []
        data = ''
        joined_data = ''

        # start time
        begin = time.time()
        while not (all(t in joined_data for t in test) or
                   ('scanfinished' in data)):
            # if data exist, then break after timeout
            if total_data and time.time() - begin > timeout:
                break

            # if no data exist, then break after longer timeout
            elif time.time() - begin > timeout * 2:
                break

            # receive data
            try:
                data = self.sock.recv(8192)
                if data:
                    print 'received "%s"' % data
                    total_data.append(data)
                    # reset start time
                    begin = time.time()
                    # join all data to final data
                    joined_data = ''.join(total_data)
                else:
                    # sleep to add time difference
                    time.sleep(0.1)
            except:
                pass

        return joined_data

    def connect(self, host, port):
        """Connect to the socket object, on host and port.

        Parameters
        ----------
        host : string
            Represent the ip address of the server to connect.

        port : int
            Represent the port address of the server to connect.
        """
        try:
            # Connect to the server at the port
            server_address = (host, port)
            print 'connecting to %s port %s' % server_address
            self.sock.connect(server_address)

            # Receive welcome reply from server
            # self.recv_timeout(3, ['Welcome'])

        except socket.error:
            print 'Failed to connect to socket.'
            sys.exit()

    def send(self, message):
        """Send data from client to server.

        Parameters
        ----------
        message : string
            Represent the message to send from the client to the server.
        """
        try:
            # Send data
            # Make compatible with Windows line breaks
            for line in message.splitlines():
                if line.endswith('\r\n'):
                    line = line
                elif line.endswith('\n'):
                    line = line[:-1] + '\r\n'
                else:
                    line = line + '\r\n'
                print 'sending "%s"' % line
                self.sock.send(line)
                self.recv_timeout(20, [line[:-2]])
                if 'stopscan' in line:
                    self.recv_timeout(20, ['scanfinished'])
                time.sleep(0.3)

        except socket.error:
            # Send failed
            print 'Sending to server failed.'
            sys.exit()

        print 'Message sent successfully.'

    def close(self):
        """Close the socket."""
        self.sock.shutdown(socket.SHUT_RDWR)
        time.sleep(0.5)
        self.sock.close()
        print('Socket closed.')
