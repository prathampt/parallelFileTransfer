import socket
import os
import threading
import zlib
from concurrent.futures import ThreadPoolExecutor
import asyncio
import time

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

        # compressed_data = self.compress_chunk(chunk_data)
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

        # Open the file and read its entire content
        with open(self.FILE_PATH, 'rb') as file:
            file_data = file.read()

        # Compress the file data using zlib
        compressed_data = zlib.compress(file_data)
        compressed_size = len(compressed_data)

        # Calculate the chunk size, ensuring it's large enough to distribute data across connections
        self.CHUNK_SIZE = max(self.CHUNK_SIZE, int(compressed_size / (self.MAX_CONNECTIONS * 4)) + 1)
        print(f"Original File Size: {file_size}, Compressed Size: {compressed_size}, Chunk Size: {self.CHUNK_SIZE}")

        # Split the compressed data into chunks
        chunks = [compressed_data[i:i + self.CHUNK_SIZE] for i in range(0, compressed_size, self.CHUNK_SIZE)]

        # Update chunk count based on the number of created chunks
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

#<__________________________________________________________Receiver Part___________________>

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
            self.SAVE_PATH = os.path.join(self.SAVE_PATH, metadata[2])
            self.CHUNK_SIZE = int(metadata[1])
            # s.send(b"ACK")

            s.close()
    # async def stop_when_done(self, servers):
    #     while self.RECEIVED_CHUNKS < self.CHUNK_COUNT:
    #         await asyncio.sleep(0.1)
    #     for server in servers:
    #         server.close()
    #         await server.wait_closed()
    #         # print("Closing servers")

            
    # async def async_receive_chunk(self, reader, writer, chunks, servers):
    #     """Receive chunk asynchronously."""       
    #     try:
    #         if self.RECEIVED_CHUNKS >= self.CHUNK_COUNT:
    #             for server in servers:
    #                 server.close()
    #                 await server.wait_closed()
    #                 print("Closing servers")
                    

    #             return
            
    #         chunk_metadata = (await reader.read(1024)).decode('utf-8')
    #         print(chunk_metadata)
    #         chunk_index, chunk_size = chunk_metadata.split('\n')
    #         chunk_index = int(chunk_index)
    #         chunk_size = int(chunk_size)
    #         writer.write(b'ACK')  # Send an "ACK" message to the client            
    #         await writer.drain()   # Ensure the message is sent
    #         print(f'Received chunk index: {chunk_index}')
            
    #         data = await reader.readexactly(chunk_size)
    #         # Send acknowledgment back to the client
    #         writer.write(b'ACK')  # Send an "ACK" message to the client
    #         await writer.drain()   # Ensure the message is sent
    #         print(f'ACK sent for chunk {chunk_index}')
            
            
    #         chunks[chunk_index] = data  # Store the received chunk
    #         self.LOCK.acquire()
    #         self.RECEIVED_CHUNKS += 1
    #         print(f"Received {self.RECEIVED_CHUNKS} chunks")
    #         self.LOCK.release()
    #         if self.RECEIVED_CHUNKS == self.CHUNK_COUNT:
    #             throw Exception("All chunks received")
                
    #     except Exception as e:
    #         print(f"Error in receiving chunk {chunk_index}: {e}")
    #     finally:
    #         self.stop_when_done(servers)

    # async def async_receive_file(self, ip):
    #     """Receive file asynchronously."""
    #     chunks = [None] * self.CHUNK_COUNT
    #     tasks = []        
    #     servers = []
    #     try:
    #         for i in range(min(self.CHUNK_COUNT, self.MAX_CONNECTIONS)):
    #             port = self.PORT + i + 1
    #             server = await asyncio.start_server(
    #                 lambda r, w: self.async_receive_chunk(r, w, chunks, servers), "0.0.0.0", port
    #             )
                
    #             tasks.append(server.serve_forever())
    #             servers.append(server)
    #             print(f'Started server for chunk {i} on port {port}')
    #         # tasks.append(self.stop_when_done(servers))
    #         await asyncio.gather(*tasks)
    #         print("All servers")

    #     except Exception as e:
    #         print(f"Error during file transfer: {e}")
    #     finally:
           

    #         self.reassemble_file(chunks)

        
    # def reassemble_file(self, chunks):
    #     """Function to reassemble the file from chunks and decompress it in the same file."""
        
    #     # Write the file from chunks
    #     with open(self.SAVE_PATH, 'wb') as file:
    #         for chunk in chunks:
    #             file.write(chunk)
    #     print("Compressed Filed Reassembled!")

    #     # Read the reassembled file and decompress it
    #     with open(self.SAVE_PATH, 'rb') as compressed_file:
    #         compressed_data = compressed_file.read()

    #     # Decompress the file data
    #     decompressed_data = zlib.decompress(compressed_data)

    #     # Overwrite the same file with decompressed data
    #     with open(self.SAVE_PATH, 'wb') as decompressed_file:
    #         decompressed_file.write(decompressed_data)
    #     print("Decompressed")
        
    # def receive_file(self):
    #     self.RECEIVED_CHUNKS = 0
    #     ip_address = socket.gethostbyname(socket.gethostname())
    #     # ip_address="10.100.97.49"
    #     print(f"Ready to receive file on IP: {ip_address}, base port: {self.PORT}")

    #     # Receive metadata
    #     self.recv_metadata(self.PORT)

    #     # Start receiving file asynchronously
    #     asyncio.run(self.async_receive_file(ip_address))
    async def stop_when_done(self, servers):
        while self.RECEIVED_CHUNKS < self.CHUNK_COUNT:
            await asyncio.sleep(0.1)
        for server in servers:
            server.close()
            await server.wait_closed()

    async def async_receive_chunk(self, reader, writer, chunks, servers):
        """Receive chunk asynchronously."""
        try:
            if self.RECEIVED_CHUNKS >= self.CHUNK_COUNT:
                raise AllChunksReceivedError("All chunks have been received.")

            chunk_metadata = (await reader.read(1024)).decode('utf-8')
            print(chunk_metadata)
            chunk_index, chunk_size = chunk_metadata.split('\n')
            chunk_index = int(chunk_index)
            chunk_size = int(chunk_size)

            writer.write(b'ACK')  # Send an "ACK" message to the client            
            await writer.drain()   # Ensure the message is sent
            print(f'Received chunk index: {chunk_index}')

            data = await reader.readexactly(chunk_size)
            writer.write(b'ACK')  # Send an "ACK" message to the client
            await writer.drain()   # Ensure the message is sent
            print(f'ACK sent for chunk {chunk_index}')

            chunks[chunk_index] = data  # Store the received chunk

            async with self.LOCK:  # Use asyncio Lock for thread safety
                self.RECEIVED_CHUNKS += 1
                print(f"Received {self.RECEIVED_CHUNKS} chunks")
                if self.RECEIVED_CHUNKS == self.CHUNK_COUNT:
                    raise AllChunksReceivedError("All chunks have been received.")

        except AllChunksReceivedError as e:
            print(e)
            # Closing servers once all chunks are received
            for server in servers:
                server.close()
                await server.wait_closed()
            print("Closing servers")

        except Exception as e:
            print(f"Error in receiving chunk {chunk_index}: {e}")

    async def async_receive_file(self, ip):
        """Receive file asynchronously."""
        chunks = [None] * self.CHUNK_COUNT
        tasks = []        
        servers = []
        try:
            for i in range(min(self.CHUNK_COUNT, self.MAX_CONNECTIONS)):
                port = self.PORT + i + 1
                server = await asyncio.start_server(
                    lambda r, w: self.async_receive_chunk(r, w, chunks, servers), "0.0.0.0", port
                )

                tasks.append(server.serve_forever())
                servers.append(server)
                servers.append(server)
                print(f'Started server for chunk {i} on port {port}')

            await asyncio.gather(*tasks)
            print("All servers are stopped")

        except AllChunksReceivedError:
            print("All chunks received, reassembling the file.")
        except Exception as e:
            print(f"Error during file transfer: {e}")
        finally:
            self.reassemble_file(chunks)

    def reassemble_file(self, chunks):
        """Function to reassemble the file from chunks and decompress it in the same file."""
        # Write the file from chunks
        with open(self.SAVE_PATH, 'wb') as file:
            for chunk in chunks:
                file.write(chunk)
        print("Compressed File Reassembled!")

        # Read the reassembled file and decompress it
        with open(self.SAVE_PATH, 'rb') as compressed_file:
            compressed_data = compressed_file.read()

        # Decompress the file data
        decompressed_data = zlib.decompress(compressed_data)

        # Overwrite the same file with decompressed data
        with open(self.SAVE_PATH, 'wb') as decompressed_file:
            decompressed_file.write(decompressed_data)
        print("File Decompressed Successfully")

    def receive_file(self):
        self.RECEIVED_CHUNKS = 0
        ip_address = socket.gethostbyname(socket.gethostname())
        print(f"Ready to receive file on IP: {ip_address}, base port: {self.PORT}")

        # Receive metadata
        self.recv_metadata(self.PORT)

        # Start receiving file asynchronously
        asyncio.run(self.async_receive_file(ip_address))

        
   

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