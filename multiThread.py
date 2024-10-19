import socket
import os
import threading
import zlib
from concurrent.futures import ThreadPoolExecutor

class parallelFileTransfer():
        
    def __init__(self, file_path = "", save_path = "") -> None:
        self.PORT = 50000
        self.MAX_CONNECTIONS = 16
        self.CHUNK_SIZE = 1024 * 1024  # 1 MB per chunk (minimum size)
        self.SAVE_PATH = save_path # input from reciever side
        self.FILE_PATH = file_path #input from sender side
        self.CHUNK_COUNT = 0 # To be recieved from the sender
        self.LOCK = threading.Lock()
        self.CONNECTION_POOL = []
        self.SERVER_POOL = []

    # Functions of SENDER...

    def get_filename(self):
        return os.path.basename(self.FILE_PATH)
    
    def send_metadata(self, ip, port):
        """Function to send the initial data about the file."""
        
        filename = self.get_filename()
        metadata = f"{self.CHUNK_COUNT}\n{self.CHUNK_SIZE}\n{filename}"
     
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((ip, port))
            s.sendall(metadata.encode('utf-8'))
            s.recv(1024)  # Recieve ACK
            s.close()

        print("Meta-data sent!")

    def create_connection_pool(self, ip):
        """Create a persistent connection pool."""

        for i in range(min(self.MAX_CONNECTIONS, self.CHUNK_COUNT)):
            conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            conn.connect((ip, self.PORT + i + 1))
            self.CONNECTION_POOL.append(conn)

        print("Connection Pool Created")

    def send_chunk(self, conn, chunk_data, chunk_index):
        """Send compressed chunk data."""

        conn.sendall(f'{chunk_index}\n{len(chunk_data)}'.encode('utf-8'))  # Send chunk index
        conn.recv(1024)  # ACK
        print(f"ChunkIndex: {chunk_index}")
        conn.sendall(chunk_data)  # Send compressed chunk data
        conn.recv(1024)  # Receive final ACK
        print(f"Chunk {chunk_index} Sent!")

    def compress_chunk(self, chunk):
        """Compress chunk using zlib."""

        return zlib.compress(chunk, level=6)
    
    def split_file(self):
        """Split the file into small chunks."""

        file_size = os.path.getsize(self.FILE_PATH)

        with open(self.FILE_PATH, 'rb') as file:
            file_data = file.read()

        compressed_data = zlib.compress(file_data)
        compressed_size = len(compressed_data)

        self.CHUNK_SIZE = max(self.CHUNK_SIZE, int(compressed_size / (self.MAX_CONNECTIONS * 4)) + 1)
        print(f"Original File Size: {file_size}, Compressed Size: {compressed_size}, Chunk Size: {self.CHUNK_SIZE}")

        # Split the compressed data into chunks
        chunks = [compressed_data[i:i + self.CHUNK_SIZE] for i in range(0, compressed_size, self.CHUNK_SIZE)]
        self.CHUNK_COUNT = len(chunks)

        return chunks
    
    def send_file(self, ip):
        """Main function to send file chunks."""

        if not self.FILE_PATH:
            raise ValueError("Invalid File Path")
        
        try:
            chunks = self.split_file()
            self.CHUNK_COUNT = len(chunks)
            self.send_metadata(ip, self.PORT)
            self.create_connection_pool(ip)

            print("Connection with the receiver established successfully!")
            
            with ThreadPoolExecutor(max_workers=self.MAX_CONNECTIONS) as executor:
                for i, chunk in enumerate(chunks):
                    conn = self.CONNECTION_POOL[i % self.MAX_CONNECTIONS]
                    executor.submit(self.send_chunk, conn, chunk, i)

        except Exception as e:
            print(f"Error Occured!\n{e}")

        finally:
            for conn in self.CONNECTION_POOL:
                conn.close()  # Ensure all connections are closed
            print("Connections closed.")

    # Functions of RECEIVER...

    def recv_metadata(self, port):
        """Function to receive the initial data about the file."""

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', port))
            s.listen()
            conn, addr = s.accept()
            metadata = conn.recv(1024).decode('utf-8')
            metadata = metadata.split('\n')
            self.CHUNK_COUNT = int(metadata[0])
            self.sender_ip = addr[0]
            self.sender_port = addr[1]
            self.SAVE_PATH = os.path.join(self.SAVE_PATH, metadata[1])

            s.close()

    def create_server_pool(self):
        """Create a persistent connection pool."""

        for i in range(min(self.MAX_CONNECTIONS, self.CHUNK_COUNT)):
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind(('', self.PORT + i + 1))
            s.listen()
            conn, addr = s.accept()
            self.SERVER_POOL.append(conn)

        print("Server Pool Created")

    def handle_receive(self, conn, chunks):

        chunk_info = conn.recv(1024).decode('utf-8')
        chunk_index, chunk_size = chunk_info.split('\n')
        chunk_index = int(chunk_index)
        chunk_size = int(chunk_size)
        conn.sendall(b'ACK')  # Acknowledge chunk index

        data = conn.recv(chunk_size)

        with self.LOCK:
            chunks.append(data)            

    def receive_file(self):
        """Main function to receive file chunks."""

        chunks = [None] * self.CHUNK_COUNT

        if not self.SAVE_PATH:
            raise ValueError("Invalid Save Path")
        
        try:
            self.recv_metadata(self.PORT)
            self.create_server_pool()

            print("Connection with the sender established successfully!")

            with ThreadPoolExecutor(max_workers=self.MAX_CONNECTIONS) as executor:
                for i in range(self.CHUNK_COUNT):
                    conn = self.SERVER_POOL[i % len(self.SERVER_POOL)]
                    executor.submit(self.handle_receive, conn, chunks)

        except Exception as e:
            print(f"Error Occured!\n{e}")

        finally:
            for conn in self.SERVER_POOL:
                conn.close()  # Ensure all servers are closed
            print("Servers closed.")


if __name__ == "__main__":

    print("Welcome to Parallel File Transfer...\n")
    print("Send File: 1")
    print("Receive File: 0")
    choice = int(input("Enter Choice: "))

    if choice:
        file_path = input("Please enter the path of file to transfer: ")
        print("Please make sure your receiver is ready!")
        ip = input("Enter the IP of Receiver: ")

        pft = parallelFileTransfer(file_path=file_path)

        pft.send_file(ip=ip)

        print("File Sent Successfully!")

    else:
        save_path = input("Please enter the path to save file: ")

        pft = parallelFileTransfer(save_path=save_path)
        
        pft.receive_file()