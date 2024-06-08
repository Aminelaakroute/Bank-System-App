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
   git clone https://github.com/your-repo/bank-system-app.git
   cd bank-system-app
