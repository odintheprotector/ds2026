'''
Practical Work 1: USTH Master File Transfer!
'''
import socket
import logging
import os

logging.basicConfig(level=logging.DEBUG)

BUFFER_SIZE = 4096
PORT = 12345

def create_client_socket(server_address, port):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((server_address, port))
    logging.info(f"Connected to server at {server_address}:{port}")
    return client_socket


def send_file(client_socket, file_path):
    if not os.path.exists(file_path):
        print("File not found!")
        return

    filename = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)

    logging.info(f"Sending file: {filename} ({file_size} bytes)")
    client_socket.send(len(filename).to_bytes(4, "big"))

    client_socket.send(filename.encode())
    client_socket.send(file_size.to_bytes(8, "big"))
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(BUFFER_SIZE)
            if not chunk:
                break
            client_socket.send(chunk)

    logging.info("File sent. Waiting for server response...")

    response = client_socket.recv(BUFFER_SIZE).decode()
    print("Server:", response)

if __name__ == "__main__":
    server_address = "localhost"
    client_socket = create_client_socket(server_address, PORT)
    try:
        while True:
            file_path = input("Enter file path to send (or 'exit'): ")
            if file_path.lower() == "exit":
                break
            send_file(client_socket, file_path)
    except KeyboardInterrupt:
        logging.info("Client shutting down.")
    finally:
        client_socket.close()
        logging.info("Connection closed.")
