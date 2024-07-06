import socket
import ssl
import time
import select
import os
import logging
from XTB.utils import generate_logger

class Client():
    """
    The Client class provides a simple interface for creating and managing

    Attributes:
    _host (str): The host address to connect to.
    _port (int): The port number to connect to.
    _encrypted (bool): Indicates whether the connection should be encrypted.
    _timeout (float): The timeout value for the connection.
    _blocking (bool): Indicates whether the connection is blocking.
    _used_addresses (list): A list of addresses that have been used.
    _family (int): The address family.
    _socktype (int): The socket type.
    _proto (int): The protocol.
    _cname (str): The canonical name.
    _sockaddr (tuple): The socket address.
    _ip_address (str): The IP address.
    _port (int): The port number.
    _socket (socket): The socket connection.
    _interval (float): The interval between requests in seconds.
    _max_fails (int): The maximum number of consecutive failed requests before giving up.
    _bytes_out (int): The maximum number of bytes to send in each request.
    _bytes_in (int): The maximum number of bytes to receive in each response.
    _stream (bool): Indicates whether to use a streaming connection.
    _logger (logging.Logger): The logger instance to use for logging.

    Methods:
        check: Check the socket for readability, writability, or errors.
        create: Creates a socket connection.
        open: Opens a connection to the server.
        send: Sends a message over the socket connection.
        receive: Receives a message from the socket.
        close: Closes the connection and releases the socket.

    """

    def __init__(self, host: str, port: int, encrypted: bool, timeout: float, stream: bool, interval: float=0.5, max_fails: int=10, bytes_out: int=1024, bytes_in: int=1024, logger=None):
        """
        Initializes a new instance of the Client class.

        Args:
            host (str): The host address to connect to.
            port (int): The port number to connect to.
            encrypted (bool): Indicates whether the connection should be encrypted.
            timeout (float): The timeout value for the connection.
            stream (bool): Indicates whether to use a streaming connection.
            interval (float, optional): The interval between requests in seconds. Defaults to 0.5.
            max_fails (int, optional): The maximum number of consecutive failed requests before giving up. Defaults to 10.
            bytes_out (int, optional): The maximum number of bytes to send in each request. Defaults to 1024.
            bytes_in (int, optional): The maximum number of bytes to receive in each response. Defaults to 1024.
            logger (logging.Logger, optional): The logger instance to use for logging. Defaults to None.

        Raises:
            ValueError: If the logger argument is provided but is not an instance of logging.Logger.
        """
        if logger:
            if not isinstance(logger, logging.Logger):
                raise ValueError("The logger argument must be an instance of logging.Logger.")
            
            self._logger = logger
        else:
            self._logger = generate_logger(name='Client', path=os.path.join(os.getcwd(), "logs"))
        
        self._host = host
        self._port = port
        self._encrypted = encrypted
        self._timeout = timeout
        
        if timeout:
            self._blocking = False
        else:
            self._blocking = True
            
        self._used_addresses = []

        self.create()

        self._interval = interval
        self._max_fails = max_fails
        self._bytes_out = bytes_out
        self._bytes_in = bytes_in
        self._stream = stream

    def check(self, mode: str):
        """
        Check the socket for readability, writability, or errors.

        Args:
            mode (str): The mode to check. Valid values are 'basic', 'readable', or 'writable'.

        Returns:
            bool: True if the socket is in the desired state, False otherwise.

        Raises:
            ValueError: If an unknown mode value is provided.

        """
        try:
            # Use select to check for readability, writability, and errors
            if mode == 'basic':
                _, _, errored = select.select([], [], [self._socket], 0)
                if self._socket in errored:
                    return False
                return True
            elif mode == 'readable':
                readable, _, _ = select.select([self._socket], [], [], 0)
                if self._socket in readable:
                    return True
                return False
            elif mode == 'writable':
                _, writable, _ = select.select([], [self._socket], [], 0)
                if self._socket in writable:
                    return True
                return False
            else:
                raise ValueError("Error: unknown mode value")
        except Exception as e:
            self._logger.error("In check method: %s" % str(e))
            return False

    def create(self):
        """
        Creates a socket connection.

        Returns:
            bool: True if the socket connection is successfully created, False otherwise.
        """
        self._logger.info("Creating socket ...")

        try:
            avl_addresses=socket.getaddrinfo(self._host, self._port, socket.AF_UNSPEC, socket.SOCK_STREAM, socket.IPPROTO_TCP)
        except socket.error as e:
            self._logger.error("Failed to query socket info: %s", e)
            return False

        self._logger.info(f"{len(avl_addresses)} addresses found")

        tried_addresses = []
        while len(tried_addresses) < len(avl_addresses):
            # Always tries those  adresses first that did not fail
            if len(self._used_addresses)+len(tried_addresses) < len(avl_addresses):
                for address in avl_addresses:
                    if address[4] not in tried_addresses and address[4] not in self._used_addresses:
                        tried_addresses.append(address)
                        break
            else:
                for address in avl_addresses:
                    if address[4] not in tried_addresses:
                        tried_addresses.append(address)
                        break
                        
            self._family, self._socktype, self._proto, self._cname, self._sockaddr = tried_addresses[-1]
            if self._family == socket.AF_INET: # For IPv4
                self._ip_address, self._port = self._sockaddr
            elif self._family == socket.AF_INET6: # For IPv6
                self._ip_address, self._port, self._flowinfo, self._scopeid = self._sockaddr 

            self._logger.info(
                "Selected socket:\nFamily: %s\nSocket Type: %s\nProtocol: %s\nCanonical Name: %s\nIP-address: %s\nPort: %s",
                self._family, self._socktype, self._proto, self._cname, self._ip_address, self._port
            )
            
            try:
                self._socket = socket.socket(self._family, self._socktype, self._proto)
            except socket.error as e:
                self._logger.error("Failed to create socket: %s", e)
                continue
            self._logger.info("Socket created")

            if self._encrypted:
                try:
                    context = ssl.create_default_context()
                    self._socket=context.wrap_socket(self._socket, server_hostname=self._host)
                except socket.error as e:
                    self._logger.error("Failed to wrap socket: %s", e)
                    continue
                self._logger.info("Socket wrapped")

            self._socket.setblocking(self._blocking)

            # safe used address
            self._used_addresses.append(self._sockaddr)

            return True

        self._used_addresses=[]
        
        self._logger.error("All attempts to create socket failed")
        return False

    def open(self):
        """
        Opens a connection to the server.

        Returns:
            bool: True if the connection is successfully opened, False otherwise.
        """
        self._logger.info("Opening connection ...")

        if not self.check(mode='basic'):
            self._logger.error("Socket failed. Try to create again")
            if not self.create():
                return False
                
        for _ in range(self._max_fails):
            try:
                if self._timeout:
                    self._socket.settimeout(self._timeout)
                self._socket.connect((self._sockaddr))
            except socket.error as error_msg:
                self._logger.error("Socket error: %s" % error_msg)
                time.sleep(self._interval)
                continue
            self._logger.info("Socket connected")
            return True
        return False

    def send(self, msg):
        """
        Sends a message over the socket connection.

        Args:
            msg (str): The message to be sent.

        Returns:
            bool: True if the message was sent successfully, False otherwise.
        """
        self._logger.info("Sending message ...")

        msg = msg.encode("utf-8")
        send_msg = 0
        while send_msg < len(msg):
            package_size = min(self._bytes_out, len(msg) - send_msg)
            try:
                if self.check(mode='writable'):
                    send_msg += self._socket.send(msg[send_msg:send_msg + package_size])
                else:
                    self._logger.error("Connection to socket broken")
                    return False
            except Exception as e:
                self._logger.error("Error sending message: %s" % str(e))
                return False
            
            time.sleep(self._interval)

        self._logger.info("Message sent")
        return True

    def receive(self):
        """
        Receives a message from the socket.

        Returns:
            str: The received message.

        Raises:
            Exception: If there is an error receiving the message.
        """
        self._logger.info("Receiving message ...")

        full_msg = ''
        while True:
            msg=''
            try:
                if self.check(mode='readable'):
                    msg = self._socket.recv(self._bytes_in)
            except Exception as e:
                self._logger.error("Error receiving message: %s" % str(e))
                return False
            
            if len(msg) > 0:
                full_msg += msg.decode("utf-8")

            if self._stream and len(msg) > 0:
                break
            elif not self._stream and len(msg) <= 0:
                break

            time.sleep(self._interval)
    
        self._logger.info("Message received")
        return full_msg

    def __del__(self):
        """
        Clean up resources and close the connection.

        This method is automatically called when the object is about to be destroyed.
        It ensures that any open connections are closed properly and any resources
        are released.

        """
        self.close()

    def close(self):
        """
        Closes the connection and releases the socket.

        Returns:
            bool: True if the connection was successfully closed, False otherwise.
        """
        # no false return function must run through

        self._logger.info("Closing connection ...")

        if self._socket.fileno() != -1:
            try:
                self._socket.shutdown(socket.SHUT_RDWR)
                self._logger.info("Connections closed")
            except Exception as e:
                self._logger.error("Error shutting down socket: %s" % str(e))
            finally:
                self._socket.close()
                self._used_addresses.pop() #stable sockets are relieved
                self._logger.info("Socket closed")
                return True
        else:
            self._logger.error("Socket is already closed")
            return True
        
    def get_host(self):
        return self._host
    
    def set_host(self, host):
        raise AttributeError("Cannot set read-only attribute 'host'")
    
    def get_port(self):
        return self._port
    
    def set_port(self, port):
        raise AttributeError("Cannot set read-only attribute 'port'")

    def get_encrypted(self):
        return self._encrypted

    def set_encrypted(self, encrypted):
        raise AttributeError("Cannot set read-only attribute 'encrypted'")
    
    def get_timeout(self):
        return self._timeout
    
    def set_timeout(self, timeout):
        self._timeout = timeout
        self._socket.settimeout(timeout)
        
        if timeout:
            self._blocking=False
        else:
            self._blocking=True

    def get_interval(self):
        return self._interval

    def set_interval(self, interval):
        self._interval = interval

    def get_max_fails(self):
        return self._max_fails

    def set_max_fails(self, max_fails):
        self._max_fails = max_fails

    def get_bytes_out(self):
        return self._bytes_out

    def set_bytes_out(self, bytes_out):
        self._bytes_out = bytes_out

    def get_bytes_in(self):
        return self._bytes_in

    def set_bytes_in(self, bytes_in):
        self._bytes_in = bytes_in

    
    host = property(get_host, set_host, doc='read only property socket host')
    port = property(get_port, set_port, doc='read only property socket port')
    encrypted = property(get_encrypted, set_encrypted, doc='read only property socket encryption')
    timeout = property(get_timeout, set_timeout, doc='Get/set the socket timeout')
    interval = property(get_interval, set_interval, doc='Get/set the interval value')
    max_fails = property(get_max_fails, set_max_fails, doc='Get/set the max fails value')
    bytes_out = property(get_bytes_out, set_bytes_out, doc='Get/set the bytes out value')
    bytes_in = property(get_bytes_in, set_bytes_in, doc='Get/set the bytes in value')
