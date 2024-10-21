<p align="center">
  <img src="https://img.icons8.com/?size=512&id=uEnXkP73YCdC&format=png" width="150" />
</p>

<p align="center">
    <h1 align="center">Parallel File Transfer</h1>
</p>


<p align="center">
    <img src="https://img.shields.io/github/license/prathampt/parallelFileTransfer?style=flat&color=0DBE70" alt="license">
  	<img src="https://img.shields.io/github/last-commit/prathampt/parallelFileTransfer?style=flat&logo=git&logoColor=white&color=50C878" alt="last-commit">
  	<img src="https://img.shields.io/github/languages/top/prathampt/parallelFileTransfer?style=flat&color=0080ff" alt="repo-top-language">
  	<img src="https://img.shields.io/github/languages/count/prathampt/parallelFileTransfer?style=flat&color=0080ff" alt="repo-language-count">
</p>

A Python-based file transfer application that accelerates the transmission of large files by utilizing **parallel TCP connections**, breaking files into smaller chunks and transmitting them concurrently. It enhances speed, reliability, and efficiency in file transfers, perfect for large data transfers across a congested networks.

## 🚀 Features
- **Parallel Transmission**: Utilizes multiple TCP connections to transfer file chunks concurrently.
- **Progress Monitoring**: Displays transfer speed, percentage completed, and estimated time remaining.
- **Error Handling**: Gracefully handles interruptions during transfer.

## 🛠️ Installation

### Prerequisites
- **Python 3.x**
- Required Libraries:
  - `socket`
  - `threading`
  - `os`
  - `time`

### Clone the Repository
```bash
git clone https://github.com/prathampt/parallelFileTransfer.git
cd parallelFileTransfer
```

## Methodology
The application is designed around the concept of **parallelism** in file transmission. Here's how it works:

### 1. File Chunking
The file to be transferred is divided into smaller chunks, each of which can be sent over separate TCP connections. The client sends these chunks concurrently to the server using multiple threads.

### 2. Parallel TCP Connections
Instead of transmitting the file sequentially, the application opens multiple **TCP connections**. Each connection handles a specific chunk of the file, reducing overall transfer time by utilizing network bandwidth more effectively.

### 3. Real-time Progress Monitoring
The application calculates and displays:
- **Percentage Complete**: Shows how much of the file has been transferred.
- **Transfer Speed**: Calculates the speed in MB/s.
- **Estimated Time Remaining**: Dynamically estimates how long the transfer will take to complete based on the current speed.

### 4. Error Handling
If a connection is interrupted, the application catches the error and ensures no data is lost or corrupted, resuming the transfer where it left off.

## 🔧 Usage

### Starting the Server
Run the server script to start receiving file chunks. The server listens on a specified port and waits for connections from clients.
```bash
python main.py -r receiver -s ./data/
```

### Sending Files as a Client
Run the client script, specifying the file to transfer and the server's IP address. The client breaks the file into chunks and sends them over multiple TCP connections.
```bash
python main.py -r sender <file_path> <receiver_ip>
```

## ⚙️ Configuration
You can adjust the number of parallel connections and the chunk size by modifying the corresponding variables in the code.

## 🛠️ Future Enhancements
- **Encryption**: Implement end-to-end encryption for secure file transfers.
- **Compression**: Add file compression to reduce the amount of data sent over the network.
- **Better error handling**: Improve recovery from network interruptions.

## 🤝 Contributing
Contributions are welcome! Please open an issue or submit a pull request to contribute.

<details closed>
    <summary>Contributing Guidelines</summary>

1. **Fork the Repository**: Start by forking the project repository to your GitHub account.
2. **Clone Locally**: Clone the forked repository to your local machine using a Git client.
   ```sh
   git clone https://github.com/prathampt/parallelFileTransfer
   ```
3. **Create a New Branch**: Always work on a new branch, giving it a descriptive name.
   ```sh
   git checkout -b new-feature-x
   ```
4. **Make Your Changes**: Develop and test your changes locally.
5. **Commit Your Changes**: Commit with a clear message describing your updates.
   ```sh
   git commit -m 'Implemented new feature x.'
   ```
6. **Push to GitHub**: Push the changes to your forked repository.
   ```sh
   git push origin new-feature-x
   ```
7. **Submit a Pull Request**: Create a PR against the original project repository. Clearly describe the changes and their motivations.

Once your PR is reviewed and approved, it will be merged into the main branch.

</details>


## License
This project is licensed under the *GNU GENERAL PUBLIC LICENSE Version 3* - see the [LICENSE](LICENSE) file for details.

### Fork and Star..
Don't forget to fork the repository and give a star if you liked it...
