import socket
import logging


class Server:
    RAW_MESSAGE_DELIMITER = b'\n'
    SOCKET_BUFFER_SIZE = 1024
    CHAR_ENCODING = 'utf-8'
    
    def __init__(self, port, listen_backlog):
        # Initialize server socket
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.bind(('', port))
        self._server_socket.listen(listen_backlog)

    def run(self):
        """
        Dummy Server loop

        Server that accept a new connections and establishes a
        communication with a client. After client with communucation
        finishes, servers starts to accept new connections again
        """

        # TODO: Modify this program to handle signal to graceful shutdown
        # the server
        while True:
            client_sock = self.__accept_new_connection()
            self.__handle_client_connection(client_sock)

    def __handle_client_connection(self, client_sock):
        """
        Read message from a specific client socket and closes the socket

        If a problem arises in the communication with the client, the
        client socket will also be closed
        """
        try:
            addr = client_sock.getpeername()
            data = b""
            delimiter = self.RAW_MESSAGE_DELIMITER
            
            while delimiter not in data:
                chunk = client_sock.recv(self.SOCKET_BUFFER_SIZE)
                
                if not chunk:
                    raise ConnectionError("Client disconnected during reception")
                
                data += chunk

            msg = data.strip().decode(self.CHAR_ENCODING)
            
            logging.info(f'action: receive_message | result: success | ip: {addr[0]} | msg: {msg}')
            
            raw_encoded_msg = f"{msg}\n".encode(self.CHAR_ENCODING)
            client_sock.sendall(raw_encoded_msg)
            
        except OSError as e:
            logging.error("action: receive_message | result: fail | error: {e}")
            
        finally:
            client_sock.close()

    def __accept_new_connection(self):
        """
        Accept new connections

        Function blocks until a connection to a client is made.
        Then connection created is printed and returned
        """

        # Connection arrived
        logging.info('action: accept_connections | result: in_progress')
        c, addr = self._server_socket.accept()
        logging.info(f'action: accept_connections | result: success | ip: {addr[0]}')
        return c
