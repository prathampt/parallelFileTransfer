import socket
import os
import threading
import zlib
from concurrent.futures import ThreadPoolExecutor
import asyncio
# import time

class parallelFileTransfer():
        
    def __init__(self, file_path = "", save_path = "") -> None:
        self.PORT = 50000
        self.MAX_CONNECTIONS = 16
        self.CHUNK_SIZE = 1024 * 1024  # 1 MB per chunk (minimum size)
        self.SAVE_PATH = save_path
        self.FILE_PATH = file_path
        self.CHUNK_COUNT = 0 # To be recieved from the sender
        self.LOCK = threading.Lock()
        self.CONNECTION_POOL = []

    def get_filename(self):
        return os.path.basename(self.FILE_PATH)
    
    # def get_bandwidth_send_metadata(self, ip, port):
    #     """Function to estimate the bandwidth using TCP window size and RTT."""
        
    #     with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    #         start_time = time.time()
    #         s.connect((ip, port))
    #         end_time = time.time()

    #         s.sendall(self.get_metadata().encode('utf-8'))
    #         s.recv(1024)  # Recieve ACK
            
    #         rtt = end_time - start_time
    #         tcp_window_size = s.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF)
            
    #         s.close()
        
    #     # Calculate the bandwidth in bits per second (bps)
    #     # Multiply by 8 to convert bytes to bits
    #     bandwidth = (tcp_window_size / rtt) * 8
        
    #     return bandwidth
        
    def send_metadata(self, ip, port):
        """Function to send the initial data about the file."""
        
        filename = self.get_filename()
        metadata = f"{self.CHUNK_COUNT}\n{filename}"
     
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((ip, port))
            s.sendall(metadata.encode('utf-8'))
            s.recv(1024)  # Recieve ACK
            s.close()
        return 

    def create_connection_pool(self, ip):
        """Create a persistent connection pool."""

        for i in range(self.MAX_CONNECTIONS):
            conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            conn.connect((ip, self.PORT + i + 1))
            self.CONNECTION_POOL.append(conn)
     
    def send_chunk(self, conn, chunk_data, chunk_index):
        """Send compressed chunk data."""

        compressed_data = self.compress_chunk(chunk_data)
        conn.sendall(f'{chunk_index}'.encode('utf-8'))  # Send chunk index
        conn.recv(1024)  # ACK
        conn.sendall(compressed_data)  # Send compressed chunk data
        conn.recv(1024)  # Receive final ACK

    def compress_chunk(self, chunk):
        """Compress chunk using zlib."""

        return zlib.compress(chunk)

    def split_file(self):
        """Split the file into small chunks."""

        file_size = os.path.getsize(self.FILE_PATH)
        chunks = []

        self.CHUNK_SIZE = max(self.CHUNK_SIZE, file_size / (self.MAX_CONNECTIONS * 4) + 1)

        with open(self.FILE_PATH, 'rb') as file:
            while file.tell() < file_size:
                chunks.append(file.read(self.CHUNK_SIZE))

        return chunks

    def send_file(self, ip):
        """Main function to send file chunks."""

        if not self.FILE_PATH:
            raise ValueError("Invalid File Path")
        
        chunks = self.split_file()
        self.CHUNK_COUNT = len(chunks)

        self.create_connection_pool(ip)

        self.send_metadata(ip)
        
        print("Connection with the receiver established successfully!")

        # Thread pool for pipelined chunk sending
        with ThreadPoolExecutor(max_workers=self.MAX_CONNECTIONS) as executor:
            for i, chunk in enumerate(chunks):
                conn = self.CONNECTION_POOL[i % len(self.CONNECTION_POOL)]  # Round-robin across connections
                executor.submit(self.send_chunk, conn, chunk, i)

    # def handle_receive(self, conn):
    #     """Function to handle incoming connections and store file chunks."""

    #     try:
    #         # Receive chunk index first
    #         chunk_index = int(conn.recv(1024).decode('utf-8'))
    #         conn.sendall(b'ACK')  # Acknowledge the index
    #         # Receive chunk data
    #         data = b""
    #         while True:
    #             part = conn.recv(1024)
    #             if not part: break
    #             data += part

    #     finally:
    #         conn.close()

    #     return data, chunk_index

    async def async_receive_chunk(self, reader, writer, chunk_index, chunks):
        """Receive chunk asynchronously."""

        writer.write(f"{chunk_index}\n".encode())
        await writer.drain()
        await reader.read(1024)  # Wait for ACK
        compressed_chunk = await reader.read(self.CHUNK_SIZE)
        chunk = zlib.decompress(compressed_chunk)  # Decompress
        self.LOCK.acquire()
        chunks[chunk_index] = chunk
        self.LOCK.release()

    async def async_receive_file(self, ip, chunk_count):
        """Receive file asynchronously."""
        chunks = [None] * chunk_count
        tasks = []

        for i in range(chunk_count):
            reader, writer = await asyncio.open_connection(ip, self.BASE_PORT + i)
            task = self.async_receive_chunk(reader, writer, i, chunks)
            tasks.append(task)

        await asyncio.gather(*tasks)

        self.reassemble_file(chunks)

    # def start_receiving(self, port, chunks):
    #     """Function to start the server to receive a file chunk."""

    #     with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:

    #         s.bind(('', port))
    #         s.listen()
    #         conn, addr = s.accept()
    #         data, chunk_index = self.handle_receive(conn)
    #         s.close()

    #     self.LOCK.acquire()
    #     chunks[chunk_index] = data
    #     self.LOCK.release()
        
    def reassemble_file(self, chunks):
        """Function to reassemble the file from chunks."""
        
        with open(self.SAVE_PATH, 'wb') as file:
            for chunk in chunks:
                file.write(chunk)

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
            self.SAVE_PATH = metadata[1]

            s.close()

    def receive_file(self):
        """Main function to receive file."""

        ip_address = socket.gethostbyname(socket.gethostname())
        print(f"Ready to receive file on IP: {ip_address}, base port: {self.PORT}")

        # Receive metadata
        self.recv_metadata(self.PORT)

        # Start receiving file asynchronously
        asyncio.run(self.async_receive_file(ip_address, self.CHUNK_COUNT))
        
    # def receive_file(self):
    #     """Main function to receive file chunks over multiple connections."""
        
    #     ip_address = socket.gethostbyname(socket.gethostname())
    #     print(f"Ready to Receive File on IP Address: {ip_address} starting from base Port: {self.PORT}")
        
    #     self.recv_metadata(self.PORT)
    #     print("Connection with the sender established successfully!")

    #     chunks = [None] * self.CHUNK_COUNT  # Initialize a list to store received chunks

    #     threads = []
    #     for i in range(self.CHUNK_COUNT):
    #         port = self.PORT + i + 1
    #         thread = threading.Thread(target=self.start_receiving, args=(port, chunks))
    #         threads.append(thread)
    #         thread.start()

    #     for thread in threads:
    #         thread.join()

    #     self.reassemble_file(chunks)
    #     print("File reassembled successfully!")


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