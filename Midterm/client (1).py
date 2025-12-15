#!/usr/bin/env python3
"""
Client to connect to the MPI Remote Shell Server

Protocol format:
AUTH_TOKEN | MSG_TYPE | PAYLOAD(JSON)

Run: python3 client.py [host] [port]
"""

import socket
import sys
import json

AUTH_TOKEN = "MPI_ACADEMIC_LAB"


def build_message(msg_type, payload):
    """
    Build protocol message:
    AUTH_TOKEN|MSG_TYPE|PAYLOAD\n
    """
    return f"{AUTH_TOKEN}|{msg_type}|{json.dumps(payload)}\n"


def main():
    # Read CLI arguments; if missing, ask interactively
    if len(sys.argv) > 1:
        host = sys.argv[1]
    else:
        host = input("Server host (IP or domain) [localhost]: ").strip() or "localhost"

    if len(sys.argv) > 2:
        port_str = sys.argv[2]
    else:
        port_str = input("Server port [9999]: ").strip() or "9999"

    try:
        port = int(port_str)
    except ValueError:
        print("ERROR: Port must be an integer.")
        sys.exit(1)

    print(f"Connecting to {host}:{port}...")

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, port))
        print("Connected!\n")

        while True:
            data = sock.recv(4096)
            if not data:
                break

            msg = data.decode(errors="replace")
            print(msg, end="")

            if "mpi>" in msg:
                try:
                    cmd = input().strip()
                    if not cmd:
                        continue

                    if cmd == "exit":
                        sock.send(build_message("EXIT", {}).encode())
                        break
                    else:
                        payload = {"cmd": cmd}
                        sock.send(build_message("EXEC", payload).encode())

                except KeyboardInterrupt:
                    print()
                    sock.send(build_message("EXIT", {}).encode())
                    break

    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        sock.close()
        print("\nDisconnected.")


if __name__ == "__main__":
    main()
