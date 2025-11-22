'''
Practical Work 1: USTH Master File Transfer!
'''
import socket
import threading
import logging
import os

logging.basicConfig(level=logging.DEBUG)

BUFFER_SIZE = 4096
PORT = 12345
SAVE_FOLDER = "received_files"

def create_server_socket(port):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(('', port))
    server_socket.listen(5)
    logging.info(f"Server listening on port {port}")

    if not os.path.exists(SAVE_FOLDER):
        os.makedirs(SAVE_FOLDER)

    return server_socket


def handle_client_connection(client_socket):
    try:
        # --- Receive filename ---
        filename_size = client_socket.recv(4)
        if not filename_size:
            return
        filename_length = int.from_bytes(filename_size, "big")

        filename = client_socket.recv(filename_length).decode()
        logging.info(f"Receiving file: {filename}")

        # --- Receive file size ---
        file_size_data = client_socket.recv(8)
        file_size = int.from_bytes(file_size_data, "big")
        logging.info(f"Expected size: {file_size} bytes")

        # --- Receive file content ---
        received = 0
        file_path = os.path.join(SAVE_FOLDER, filename)

        with open(file_path, "wb") as f:
            while received < file_size:
                chunk = client_socket.recv(BUFFER_SIZE)
                if not chunk:
                    break
                f.write(chunk)
                received += len(chunk)

        logging.info(f"File saved: {file_path}")
        client_socket.send(b"File received OK")

    except Exception as e:
        logging.error(f"Error: {e}")

    finally:
        client_socket.close()
        logging.info("Closed client connection.")


def start_server(port):
    server_socket = create_server_socket(port)
    while True:
        client_socket, addr = server_socket.accept()
        logging.info(f"Accepted connection from {addr}")
        threading.Thread(target=handle_client_connection, args=(client_socket,)).start()


if __name__ == "__main__":
    start_server(PORT)
