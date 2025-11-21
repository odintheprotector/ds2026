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
#usth spoiler alert client.py
import socket
import logging
logging.basicConfig(level=logging.DEBUG)
BUFFER_SIZE = 4096
PORT = 12345

#create a while-loop to connect to the server and request spoiler alerts
def create_client_socket(server_address, port):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((server_address, port))
    logging.info(f"Connected to server at {server_address}:{port}")
    return client_socket
def request_spoiler_alert(client_socket, message):
    client_socket.send(message.encode())
    logging.info(f"Sent message: {message}")
    data = client_socket.recv(BUFFER_SIZE)
    logging.info(f"Received spoiler alert: {data.decode()}")
    return data.decode()
if __name__ == "__main__":
    server_address = 'localhost'  # Change to server IP if needed
    client_socket = create_client_socket(server_address, PORT)
    try:
        while True:
            message = str(input("Your message: "))
            spoiler_alert = request_spoiler_alert(client_socket, message)
            print(f"Spoiler Alert from Server: {spoiler_alert}")
    except KeyboardInterrupt:
        logging.info("Client shutting down.")   
        
    finally:
        client_socket.close()
        logging.info("Connection closed.")
