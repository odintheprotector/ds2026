import grpc
import logging
import os
import uuid
import threading
import time
from queue import Queue

import file_transfer_pb2 as pb2
import file_transfer_pb2_grpc as pb2_grpc

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(threadName)s - %(message)s')

SERVER_ADDRESS = "localhost"
PORT = 50051
CHUNK_SIZE = 4096 * 10  # Larger chunk size for efficiency
MAX_RETRIES = 3
SECRET_KEY = "USTH_RPC_SECRET_2025" 
MAX_WORKERS = 5 # For parallel uploads

# Global queue for tasks (file paths)
file_queue = Queue()

def generate_file_chunks(transfer_id, file_path, secret_key):
    """A generator that yields FileChunk messages, implementing chunking."""
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    filename = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)
    
    logging.info(f"Transfer ID {transfer_id}: Preparing to send file {filename} ({file_size} bytes).")

    chunk_index = 0
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break
            
            # The first chunk includes metadata and the secret key
            if chunk_index == 0:
                yield pb2.FileChunk(
                    transfer_id=transfer_id,
                    filename=filename,
                    file_size=file_size,
                    secret_key=secret_key,
                    chunk_index=chunk_index,
                    content=chunk
                )
            else:
                yield pb2.FileChunk(
                    transfer_id=transfer_id,
                    chunk_index=chunk_index,
                    content=chunk
                )
            chunk_index += 1
            
def send_file_with_retry(stub, file_path):
    """Handles a single file upload, including retry logic."""
    for attempt in range(MAX_RETRIES):
        transfer_id = str(uuid.uuid4())
        
        logging.info(f"Transfer ID {transfer_id}: Attempt {attempt + 1}/{MAX_RETRIES} for file {os.path.basename(file_path)}.")
        
        try:
            # Call the remote procedure, passing the generator as the stream
            chunk_generator = generate_file_chunks(transfer_id, file_path, SECRET_KEY)
            response = stub.UploadFile(chunk_generator)

            # Check the response status
            if response.status == pb2.TransferStatus.SUCCESS:
                print(f"SUCCESS (ID: {response.transfer_id}): {response.message} - File: {os.path.basename(file_path)}")
                return True
            
            elif response.status == pb2.TransferStatus.UNAUTHENTICATED:
                print(f"UNAUTHENTICATED (ID: {response.transfer_id}): {response.message} - File: {os.path.basename(file_path)}. Cannot retry.")
                return False

            elif response.status == pb2.TransferStatus.FAILURE:
                logging.warning(f"Transfer ID {transfer_id}: Failed: {response.message}. Retrying...")
                time.sleep(2 * (attempt + 1)) # Exponential backoff
                continue

        except grpc.RpcError as e:
            # Connection errors, timeouts, etc.
            logging.error(f"Transfer ID {transfer_id}: RPC Error on attempt {attempt + 1}: {e.details()}")
            time.sleep(2 * (attempt + 1))
            continue
        except FileNotFoundError as e:
            print(f"File not found: {file_path}")
            return False
            
    # If the loop completes without returning True
    print(f"FAILED: File {os.path.basename(file_path)} failed after {MAX_RETRIES} attempts.")
    return False

def worker(channel):
    """Worker thread that processes the file queue."""
    stub = pb2_grpc.FileTransferServiceStub(channel)
    while True:
        file_path = file_queue.get()
        if file_path is None:
            # Stop signal received
            break
        send_file_with_retry(stub, file_path)
        file_queue.task_done()

if __name__ == "__main__":
    # Create a single channel, threads will share it
    channel = grpc.insecure_channel(f'{SERVER_ADDRESS}:{PORT}')
    
    # Start worker threads for parallel uploads
    threads = []
    for i in range(MAX_WORKERS):
        t = threading.Thread(target=worker, args=(channel,))
        t.start()
        threads.append(t)
        
    try:
        print(f"Client started with {MAX_WORKERS} parallel workers.")
        while True:
            file_path = input("Enter file path to send (or 'exit'): ")
            if file_path.lower() == "exit":
                break
            # Add the file path to the queue for a worker to pick up
            file_queue.put(file_path)
            
    except KeyboardInterrupt:
        logging.info("Client shutting down.")
    
    finally:
        # Wait for all queued tasks to be finished
        file_queue.join()
        
        # Stop worker threads by sending None to the queue
        for _ in range(MAX_WORKERS):
            file_queue.put(None)
            
        for t in threads:
            t.join()
            
        channel.close()
        logging.info("Connection closed.")
