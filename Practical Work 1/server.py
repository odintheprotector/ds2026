'''
Practical Work 1: USTH Master Spoiler Alert!
• socket(): Creates a socket, a communications endpoint
• setsockopt(): Set options on a socket
• bind(): Associate a socket with an address
• gethostbyname(): Get the the address of the machine with
a given name
• listen(): Listen for machines trying to connect to this
machine
• connect(): Establish a connection with another machine
• accept(): Accept a connection
• send(): Send data over a connection
• recv(): Read data from a connection
'''
#usth_spoiler_alert_server.py
import socket
import threading
import logging
logging.basicConfig(level=logging.DEBUG)
BUFFER_SIZE = 4096
PORT = 12345
SPOILER_DATA = "Hello, this is a spoiler alert message from USTH Master!"
def create_server_socket(port):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(('', port))
    server_socket.listen(5)
    logging.info(f"Server listening on port {port}")
    return server_socket
def handle_client_connection(client_socket):
    try:
        while True:
            data = client_socket.recv(BUFFER_SIZE)
            if not data:
                logging.info("No data received. Closing connection.")
                break
            logging.info(f"Received data: {data.decode()}")
            client_socket.send(SPOILER_DATA.encode())
            logging.info("Sent spoiler alert data to client.")
    except:
        logging.error("Error handling client connection.")
    finally:
        client_socket.close()
        logging.info("Closed client connection.")
def start_server(port):
    server_socket = create_server_socket(port)
    while True:
        client_socket, addr = server_socket.accept()
        logging.info(f"Accepted connection from {addr}")
        client_handler = threading.Thread(
            target=handle_client_connection,
            args=(client_socket,)
        )
        client_handler.start()
if __name__ == "__main__":
    start_server(PORT)
