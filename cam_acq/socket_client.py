import socket
import sys
import time
import re

class Client(object):
    """Client class

    Attributes:
        sock: The socket
    """

    def __init__(self, sock=None):
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
        """Receives reply from server, with a timeout and a list of strings
        to test. When all test strings are received, the listening loop ends."""

        # make socket non blocking
        self.sock.setblocking(False)

        # total data in an array
        total_data=[]
        data=''
        joined_data = ''

        # start time
        begin=time.time()
        while not (all(t in data for t in test) or
                   ('scanfinished' in data)):
            # if data exist, then break after timeout
            if total_data and time.time()-begin > timeout:
                break

            # if no data exist, then break after longer timeout
            elif time.time()-begin > timeout*2:
                break

            # receive data
            try:
                data = self.sock.recv(8192)
                if data:
                    print 'received "%s"' % data
                    total_data.append(data)
                    # reset start time
                    begin=time.time()
                    # join all data to final data
                    joined_data = ''.join(total_data)
                else:
                    # sleep to add time difference
                    time.sleep(0.1)
            except:
                pass

        return joined_data

    def connect(self, host, port):
        """Connects to the socket object, on host and port.
        host: A string representing the ip address of the server to connect.
        port: An int representing the port address of the server to connect.
        """

        try:
            # Connect to the server at the port
            server_address = (host, port)
            print 'connecting to %s port %s' % server_address
            self.sock.connect(server_address)

            # Receive welcome reply from server
            self.recv_timeout(3, 'Welcome')

        except socket.error:
            print 'Failed to connect to socket.'
            sys.exit()

        return

    def send(self, message):
        """Function to send data from client to server.
        message: A string representing the message to send from the client
                     to the server.
        """
        try:
            # Send data
            # Make compatible with Windows line breaks
            for line in message.splitlines():
                if line[-2:]=='\r\n':
                    line = line
                if line[-1:]=='\n':
                    line = line[:-1] + '\r\n'
                else:
                    line = line + '\r\n'
                print 'sending "%s"' % line
                self.sock.send(line)
                self.recv_timeout(20, line[:-2])
                time.sleep(0.3)
                #if 'pmt' in line:
                    #print('Waiting for objective')
                    #time.sleep(5)

        except socket.error:
            #Send failed
            print 'Sending to server failed.'
            sys.exit()

        print 'Message sent successfully.'

        return

    def close(self):
        self.sock.shutdown(socket.SHUT_RDWR)
        time.sleep(0.5)
        self.sock.close()
        print('Socket closed.')
        return

if __name__ =='__main__':
    main(sys.argv[1:])
