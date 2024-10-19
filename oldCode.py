import socket
import os
import threading
import argparse
import time
import sys

class parallelFileTransfer():
        
    def __init__(self, file_path = "", save_path = "") -> None:
        self.PORT = 50000
        self.MAX_CONNECTIONS = 16 
        self.CHUNK_SIZE = 1024 * 1024  # 1 MB per chunk # Later to be decided dynamically
        self.SAVE_PATH = save_path
        self.FILE_PATH = file_path
        self.CHUNK_COUNT = 0 # To be recieved from the sender
        self.LOCK = threading.Lock()
        self.FILE_SIZE = 0
        self.FILE_DONE = 10 ** (-5)
        self.START_TIME = time.time()

    def display_speed(self):
        # Calculate transfer speed and remaining time
        elapsed_time = time.time() - self.START_TIME
        speed = self.FILE_DONE / elapsed_time if elapsed_time > 0 else 0
        percent_complete = (self.FILE_DONE / self.FILE_SIZE) * 100
        time_remaining = (self.FILE_SIZE - self.FILE_DONE) / speed if speed > 0 else 0

        # Display progress on terminal
        sys.stdout.write(f"\rSent: {self.FILE_DONE} / {self.FILE_SIZE} bytes ({percent_complete:.2f}%) | "
                        f"Speed: {speed / (1024 * 1024):.2f} MB/s | "
                        f"Time remaining: {time_remaining:.2f} s\n")
        sys.stdout.flush()

    def get_external_ip(self):
        hostname = socket.gethostname()
        ip_addresses = socket.getaddrinfo(hostname, None, socket.AF_INET, socket.SOCK_STREAM)
        
        # Extracting only IPv4 addresses
        ip_list = [ip[4][0] for ip in ip_addresses if ip[0] == socket.AF_INET]
        
        # Exclude local addresses (127.0.0.1) and pick the first external IP
        for ip in ip_list:
            if not ip.startswith("127."):
                return ip
        return None

    # Functions of SENDER...

    def get_filename(self):
        return os.path.basename(self.FILE_PATH)
        
    def send_metadata(self, ip, port):
        """Function to send the initial data about the file."""
        
        filename = self.get_filename()
        metadata = f"{self.CHUNK_COUNT}\n{filename}\n{self.FILE_SIZE}"
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((ip, port))
                s.sendall(metadata.encode('utf-8'))
                s.recv(1024)  # Recieve ACK
                s.close()

            print("Meta-data sent!")
        except Exception as e:
            print("Error Occured: ", e)            

    def send_chunk(self, chunk_data, chunk_index, ip, port):
        """Function to send a chunk."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((ip, port))
                
                s.sendall(f'{chunk_index}'.encode('utf-8')) # Sending chunk index 
                s.recv(1024)  # Recieve ACK
                
                s.sendall(chunk_data) # Send chunk data
                with self.LOCK:
                  self.FILE_DONE += len(chunk_data)
                self.display_speed()
                s.close()
        except Exception as e:
            print("Error Occured: ", e)

    def split_file(self, file_path):
        """Function to split the file into small chunks."""

        file_size = os.path.getsize(file_path)
        self.FILE_SIZE = file_size

        self.CHUNK_SIZE = max(self.CHUNK_SIZE, int(file_size / 16 + 1))
        
        with open(file_path, 'rb') as file:
            chunks = []
            while file.tell() < file_size:
                chunks.append(file.read(self.CHUNK_SIZE))

        return chunks

    def send_file(self, ip):
        """Main function to send file chunks."""
        if not self.FILE_PATH:
            raise ValueError("Invalid File Path")
        
        chunks = self.split_file(self.FILE_PATH)
        self.CHUNK_COUNT = len(chunks)
        self.send_metadata(ip, self.PORT)

        threads = []
        for i, chunk in enumerate(chunks):
            port = self.PORT + i + 1  # Assign a unique port for each connection
            thread = threading.Thread(target=self.send_chunk, args=(chunk, i, ip, port))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

    def handle_receive(self, conn):
        """Function to handle incoming connections and store file chunks."""

        try:
            # Receive chunk index first
            chunk_index = int(conn.recv(1024).decode('utf-8'))
            conn.sendall(b'ACK')  # Acknowledge the index
            # Receive chunk data
            data = b""
            while True:
                part = conn.recv(1024)
                if not part: break
                data += part
                with self.LOCK:
                    self.FILE_DONE += len(part)
                self.display_speed()
        except Exception as e:
            print("Error Occured: ", e)                            

        finally:
            conn.close()

        return data, chunk_index

    def start_receiving(self, port, chunks):
        """Function to start the server to receive a file chunk."""

        try:    
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(('', port))
                s.listen()
                conn, addr = s.accept()
                data, chunk_index = self.handle_receive(conn)
                s.close()

            self.LOCK.acquire()
            chunks[chunk_index] = data
            self.LOCK.release()
        except Exception as e:
            print("Error Occured: ", e)
            
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
            self.SAVE_PATH += metadata[1]
            self.FILE_SIZE = int(metadata[2])

                s.close()
        except Exception as e:
            print("Error Occured: ", e)
        
    def receive_file(self):
        """Main function to receive file chunks over multiple connections."""

        ip_address = self.get_external_ip()
        print(f"Ready to Receive File on IP Address: {ip_address}")
        
        self.recv_metadata(self.PORT)
        
        chunks = [None] * self.CHUNK_COUNT  # Initialize a list to store received chunks

        threads = []
        for i in range(self.CHUNK_COUNT):
            port = self.PORT + i + 1
            thread = threading.Thread(target=self.start_receiving, args=(port, chunks))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        self.reassemble_file(chunks)
        print("File received successfully!")

if __name__ == "__main__":
    # Initialize argument parser
    parser = argparse.ArgumentParser(description="Parallel File Transfer")

    # Add arguments
    parser.add_argument("-r", "--role", help="Specify the role as 'sender' or 'receiver'", choices=['sender', 'receiver'])
    parser.add_argument("file_path", nargs='?', help="Path of the file to transfer (only for sender)")
    parser.add_argument("ip", nargs='?', help="IP address of the receiver (only for sender)")
    parser.add_argument("-s", "--save_path", help="Path to save the file (only for receiver)")

    # Parse the arguments
    args = parser.parse_args()

    # Main logic based on role
    if args.role == "sender":
        # Handle missing file path
        if not args.file_path:
            args.file_path = input("Please enter the path of the file to transfer: ")

        # Handle missing IP
        if not args.ip:
            args.ip = input("Please enter the IP of the receiver: ")

        print("Please make sure your receiver is ready!")
        
        pft = parallelFileTransfer(file_path=args.file_path)
        pft.send_file(ip=args.ip)
        print("File Sent Successfully!")

    elif args.role == "receiver":
        # Handle missing save path
        if not args.save_path:
            args.save_path = input("Please enter the path to save the file: ")

        pft = parallelFileTransfer(save_path=args.save_path)
        pft.receive_file()

    else:
        print("Invalid role. Please use -r 'sender' or 'receiver'.")