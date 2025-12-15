#!/usr/bin/env python3
"""
MPI Remote Shell Server - Supports multiple TCP clients
Protocol format:
AUTH_TOKEN | MSG_TYPE | PAYLOAD(JSON)

Run: mpirun -np 4 python3 servermpi.py
"""

from mpi4py import MPI
import socket
import subprocess
import threading
import json
import time
import sys

# ============================== CONFIG ==============================
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 9999
CMD_TIMEOUT = 10
MAX_CLIENTS = 10

AUTH_TOKEN = "MPI_ACADEMIC_LAB"

ALLOWED_COMMANDS = [
    "ls", "pwd", "whoami", "hostname", "uptime",
    "date", "df", "free", "cat", "echo", "uname"
]
# ====================================================================

comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()


def log(msg: str) -> None:
    print(f"[Rank {rank}] [{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def is_command_allowed(cmd: str) -> bool:
    if not cmd.strip():
        return False
    return cmd.strip().split()[0] in ALLOWED_COMMANDS


def execute_command(cmd: str) -> str:
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            timeout=CMD_TIMEOUT,
            text=True,
            env={"PATH": "/usr/bin:/bin", "LANG": "C"}
        )
        output = (result.stdout or "") + (result.stderr or "")
        return output if output else "[No output]"
    except subprocess.TimeoutExpired:
        return "[ERROR] Command timeout"
    except Exception as e:
        return f"[ERROR] {str(e)}"


# ========================= CONTROLLER (Rank 0) =========================
def controller_main() -> None:
    if size < 2:
        print("ERROR: Need at least 2 processes. Run: mpirun -np 4 python3 servermpi.py")
        sys.exit(1)

    log(f"MPI Remote Shell Server started with {size - 1} worker(s)")
    log(f"Listening on {SERVER_HOST}:{SERVER_PORT}")

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        server.bind((SERVER_HOST, SERVER_PORT))
        server.listen(MAX_CLIENTS)
    except Exception as e:
        log(f"ERROR binding socket: {e}")
        sys.exit(1)

    def handle_client(client_sock: socket.socket, addr) -> None:
        client_id = f"{addr[0]}:{addr[1]}"
        log(f"Client connected: {client_id}")

        try:
            client_sock.send(b"=== MPI Remote Shell ===\n")
            client_sock.send(f"Connected to {size - 1} workers\n".encode())
            client_sock.send(b"Type 'help' for commands, 'exit' to quit\n\n")

            while True:
                client_sock.send(b"mpi> ")
                data = client_sock.recv(4096)
                if not data:
                    break

                raw = data.decode(errors="replace").strip()
                if not raw:
                    continue

                # ===== PROTOCOL PARSING =====
                try:
                    token, msg_type, payload = raw.split("|", 2)
                except ValueError:
                    client_sock.send(b"[ERROR] Invalid protocol format\n")
                    continue

                if token != AUTH_TOKEN:
                    client_sock.send(b"[ERROR] Authentication failed\n")
                    continue

                if msg_type == "EXIT":
                    client_sock.send(b"Goodbye!\n")
                    break

                if msg_type != "EXEC":
                    client_sock.send(b"[ERROR] Unknown message type\n")
                    continue
                #payload
                try:
                    payload_json = json.loads(payload)
                    cmd = payload_json.get("cmd", "").strip()
                except json.JSONDecodeError:
                    client_sock.send(b"[ERROR] Invalid JSON payload\n")
                    continue

                if not cmd:
                    client_sock.send(b"[ERROR] Empty command\n")
                    continue

                if cmd == "help":
                    help_text = "Available commands:\n" + "\n".join(f"  - {c}" for c in ALLOWED_COMMANDS)
                    help_text += "\n  - help\n  - workers\n  - exit\n"
                    client_sock.send(help_text.encode())
                    continue

                if cmd == "workers":
                    client_sock.send(f"Active workers: {size - 1}\n".encode())
                    continue

                if not is_command_allowed(cmd):
                    client_sock.send(b"[ERROR] Command not allowed\n")
                    continue

                log(f"Client {client_id} executes: {cmd}")

                task = {"cmd": cmd, "client": client_id}
                comm.bcast(task, root=0)

                results = comm.gather(None, root=0)

                output = f"\n{'=' * 50}\n"
                for i, result in enumerate(results[1:], 1):
                    output += f"[Worker {i}] {result['hostname']}\n"
                    output += f"{result['output']}\n"
                    output += f"{'-' * 50}\n"

                client_sock.send(output.encode())

        except Exception as e:
            log(f"Error handling client {client_id}: {e}")
        finally:
            client_sock.close()
            log(f"Client disconnected: {client_id}")

    try:
        while True:
            client_sock, addr = server.accept()
            threading.Thread(target=handle_client, args=(client_sock, addr), daemon=True).start()

    except KeyboardInterrupt:
        log("Shutting down server...")
        comm.bcast({"cmd": "__EXIT__", "client": "system"}, root=0)
    finally:
        server.close()


# =========================== WORKER (Rank > 0) ===========================
def worker_main() -> None:
    hostname = socket.gethostname()
    log(f"Worker ready on {hostname}")

    while True:
        task = comm.bcast(None, root=0)

        if task["cmd"] == "__EXIT__":
            log("Shutdown signal received")
            break

        cmd = task["cmd"]
        client = task["client"]

        log(f"Executing command from {client}: {cmd}")

        output = execute_command(cmd)
        result = {"hostname": hostname, "output": output}
        comm.gather(result, root=0)


# ================================ MAIN ================================
if __name__ == "__main__":
    if rank == 0:
        controller_main()
    else:
        worker_main()

    log("Process terminated")
