# Bank System Application

## Overview

The Bank System Application is a PyQt5-based desktop application that simulates basic banking operations such as account verification, deposit, withdrawal, transfer, and transaction history retrieval. The application uses an SSL/TLS secured client-server architecture to ensure secure communication between the client and the server.

## Features

- **Server Management**:
  - Start and stop the server.
  - Upload SSL/TLS certificate and key for secure communication.
  - Display server status.

- **Client Operations**:
  - Connect to the server.
  - Verify account using account number and PIN.
  - Perform banking operations such as deposit, withdrawal, transfer, check balance, and view transaction history.
  - Display responses from the server.

- **CSV Upload**:
  - Upload clients, accounts, and operations data from CSV files.
  - Display uploaded data in a table.

- **Database Management**:
  - Import data from an SQLite database.
  - Insert clients, accounts, and operations data into the database.

## Installation

1. **Clone the Repository**:
   ```bash
   https://github.com/Aminelaakroute/Bank-System-App.git
2. **Create and Activate a Virtual Environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
4. **Generation of SSL/TLS Certificates:**
    To generate a server certificate and private key, you can use the openssl tool. Here are the commands to generate these files:

   1. *Generate a private key*:
       ```bash
      openssl genpkey -algorithm RSA -out server_key.pem
      ```
   2. *Générer une demande de signature de certificat (CSR)*:
       ```bash
      openssl req -new -key server_key.pem -out server_csr.pem
       ```
   3. *Générer un certificat auto-signé*:
       ```bash
      openssl x509 -req -days 365 -in server_csr.pem -signkey server_key.pem -out server_cert.pem
       ```
       These steps generate two main files:

       `server_key.pem`  : The private key of the server.

       `server_cert.pem` : The server certificate.


5. **Run the Application**:
   ```bash
   python main.py
   
## Usage
- **Starting the Server**
  1. Open the application.
  2. Enter the port number in the `Port` input field.
  3. Upload the SSL/TLS certificate and key using the `Upload Certificate` and `Upload Key` buttons.
  4. Click the `Start Server` button to start the server.
  5. The server status will be displayed in the `Server Status` label.
  6. You can stop Server in `Stop Server`
- **Connecting the Client**
  1. Click the `Connect to Server` button to connect to the server.
  2. The client status will be displayed in the `Server Status` label.
  3. You can stop Client Server in `Stop Client`
  
## Contributing
Contributions are welcome! Please open an issue or submit a pull request for any improvements or bug fixes

## Acknowledgements
- PyQt5 for the GUI framework.
- SQLite for the database.
- Sockets
- Signals
- SSL/TLS for secure communication.

