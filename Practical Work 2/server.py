import grpc
from concurrent import futures
import os
import logging
import uuid
import file_transfer_pb2 as pb2
import file_transfer_pb2_grpc as pb2_grpc

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(threadName)s - %(message)s')

SAVE_FOLDER = "received_files"
PORT = 50051
VALID_SECRET_KEY = "USTH_RPC_SECRET_2025" # Hardcoded key for example

if not os.path.exists(SAVE_FOLDER):
    os.makedirs(SAVE_FOLDER)

class FileTransferServicer(pb2_grpc.FileTransferServiceServicer):
    
    def UploadFile(self, request_iterator, context):
        transfer_id = str(uuid.uuid4()) # Fallback ID, usually set by first chunk
        filename = ""
        file_handle = None
        
        try:
            # Consume the first chunk to check auth and metadata
            first_chunk = next(request_iterator)
            transfer_id = first_chunk.transfer_id
            
            # 1. Authentication Check
            if first_chunk.secret_key != VALID_SECRET_KEY:
                logging.warning(f"Transfer ID {transfer_id}: Authentication failed.")
                return pb2.TransferStatus(
                    status=pb2.TransferStatus.UNAUTHENTICATED,
                    message="Invalid secret key.",
                    transfer_id=transfer_id
                )

            # 2. Metadata Extraction
            filename = first_chunk.filename
            file_size = first_chunk.file_size
            file_path = os.path.join(SAVE_FOLDER, filename)
            
            logging.info(f"Transfer ID {transfer_id}: Receiving file {filename} ({file_size} bytes).")
            file_handle = open(file_path, "wb")
            
            # Write content of the first chunk
            file_handle.write(first_chunk.content)
            
            # 3. Stream Processing (Remaining chunks)
            chunk_count = 1
            for chunk in request_iterator:
                if chunk.chunk_index != chunk_count:
                    # Basic check for chunk order (optional but good practice)
                    logging.error(f"Transfer ID {transfer_id}: Chunk index mismatch. Expected {chunk_count}, got {chunk.chunk_index}")
                    break
                file_handle.write(chunk.content)
                chunk_count += 1
                if chunk_count % 100 == 0:
                     logging.debug(f"Transfer ID {transfer_id}: Received {chunk_count} chunks.")

            file_handle.close()
            logging.info(f"Transfer ID {transfer_id}: File saved successfully to {file_path}. Total chunks: {chunk_count}")

            return pb2.TransferStatus(
                status=pb2.TransferStatus.SUCCESS,
                message="File received OK via RPC.",
                transfer_id=transfer_id
            )
        
        except StopIteration:
            # Occurs if the client stream is empty or ends unexpectedly
            if file_handle: file_handle.close()
            logging.error(f"Transfer ID {transfer_id}: Client stream ended unexpectedly.")
            return pb2.TransferStatus(status=pb2.TransferStatus.FAILURE, message="Empty stream.", transfer_id=transfer_id)
        
        except Exception as e:
            if file_handle: file_handle.close()
            logging.error(f"Transfer ID {transfer_id}: Internal Server Error: {e}", exc_info=True)
            return pb2.TransferStatus(status=pb2.TransferStatus.FAILURE, message=f"Transfer failed: {e}", transfer_id=transfer_id)


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=20))
    pb2_grpc.add_FileTransferServiceServicer_to_server(FileTransferServicer(), server)
    server.add_insecure_port(f'[::]:{PORT}')
    server.start()
    logging.info(f"RPC Server listening on port {PORT}")
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        server.stop(0)

if __name__ == '__main__':
    serve()
