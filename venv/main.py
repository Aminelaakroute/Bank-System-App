import sys
import socket
import ssl
import threading
from PyQt5.QtWidgets import QMainWindow, QApplication, QFileDialog, QMessageBox, QTableWidgetItem, QInputDialog

from PyQt5.QtWidgets import QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, QFormLayout
from PyQt5.QtCore import Qt, QThread, pyqtSignal, pyqtSlot, QObject

from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QDesktopServices


import sqlite3
import pandas as pd
from untitled_ui import Ui_MainWindow

import socket
import ssl
import sqlite3
import threading


class ServerSignals(QObject):
    started = pyqtSignal(int)
    stopped = pyqtSignal()
    update_status_label = pyqtSignal(str)
    connectedClient = pyqtSignal(object)
    error = pyqtSignal(str)
    response_received = pyqtSignal(str)
    stoppedClient = pyqtSignal()


class ServerThread(threading.Thread):
    def __init__(self, port, server_address, certfile, keyfile, signals):
        super(ServerThread, self).__init__()
        self.port = port
        self.certfile = certfile
        self.keyfile = keyfile
        self.server_socket = None
        self.running = True
        self.server_address = server_address
        self.conn = sqlite3.connect("banque.db")
        self.signals = signals

    def run(self):
        try:
            context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            context.load_cert_chain(certfile=self.certfile, keyfile=self.keyfile)

            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.server_address, self.port))
            self.server_socket.listen(5)
            self.server_socket.settimeout(1)  # Set a timeout for the accept method
            self.signals.started.emit(self.port)
            print(f"Server started on port {self.port}")

            while self.running:
                try:
                    client_socket, addr = self.server_socket.accept()
                    print(f"Accepted connection from {addr}")
                    client_socket = context.wrap_socket(client_socket, server_side=True)
                    threading.Thread(target=self.handle_client, args=(client_socket, addr)).start()
                except socket.timeout:
                    continue  # Continue the loop if accept times out
                except Exception as e:
                    self.signals.update_status_label.emit(f"Accept error: {e}")
                    print(f"Accept error: {e}")
                    break
        except Exception as e:
            self.signals.update_status_label.emit(f"Server error: {e}")
            print(f"Server error: {e}")
        finally:
            if self.server_socket:
                self.server_socket.close()
            self.signals.update_status_label.emit("Server stopped")
            self.signals.stopped.emit()
            print("Server socket closed")

    def handle_client(self, client_socket, addr):
        with client_socket:
            while True:
                try:
                    message = client_socket.recv(1024).decode("utf-8").upper().split(" ")
                    if not message or len(message) == 0:
                        break
                    command = message[0]
                    if command == "TESTPIN" and len(message) == 3:
                        if self.testpin(message[1], message[2]):
                            client_socket.send("TESTPIN OK".encode("utf-8"))
                        else:
                            client_socket.send("TESTPIN NOK".encode("utf-8"))
                    elif command == "SOLDE" and len(message) == 2:
                        client_socket.send(("SOLDE " + str(self.solde(message[1]))).encode("utf-8"))
                    elif command == "RETRAIT" and len(message) == 3:
                        if self.retrait(message[1], message[2]):
                            client_socket.send("RETRAIT OK".encode("utf-8"))
                        else:
                            client_socket.send("RETRAIT NOK".encode("utf-8"))
                    elif command == "DEPOT" and len(message) == 3:
                        if self.depot(message[1], message[2]):
                            client_socket.send("DEPOT OK".encode("utf-8"))
                        else:
                            client_socket.send("DEPOT NOK".encode("utf-8"))
                    elif command == "TRANSFERT" and len(message) == 4:
                        if self.transfert(message[1], message[2], message[3]):
                            client_socket.send("TRANSFERT OK".encode("utf-8"))
                        else:
                            client_socket.send("TRANSFERT NOK".encode("utf-8"))
                    elif command == "HISTORIQUE" and len(message) == 2:
                        client_socket.send(("HISTORIQUE " + self.historique(message[1])).encode("utf-8"))
                    else:
                        client_socket.send("Commande non reconnue".encode("utf-8"))
                        print("Message non compris : " + " ".join(message))
                except Exception as e:
                    print(f"Client handler error: {e}")
                    break

    def connexionBaseDeDonnees(self):
        baseDeDonnees = sqlite3.connect("banque.db")
        curseur = baseDeDonnees.cursor()
        return baseDeDonnees, curseur

    def testpin(self, nocompte, pinuser):
        baseDeDonnees, curseur = self.connexionBaseDeDonnees()
        curseur.execute("SELECT PIN FROM comptes WHERE NumeroCompte = ?", (nocompte,))
        pincompte = curseur.fetchone()[0]
        baseDeDonnees.close()
        return pincompte == pinuser

    def solde(self, nocompte):
        baseDeDonnees, curseur = self.connexionBaseDeDonnees()
        curseur.execute("SELECT Solde FROM comptes WHERE NumeroCompte = ?", (nocompte,))
        soldeCompte = curseur.fetchone()[0]
        baseDeDonnees.close()
        return soldeCompte

    def retrait(self, nocompte, montant):
        baseDeDonnees, curseur = self.connexionBaseDeDonnees()
        montant = float(montant)
        soldeCompte = self.solde(nocompte)
        if soldeCompte < montant or montant <= 0:
            baseDeDonnees.close()
            return False
        else:
            nouveauSolde = soldeCompte - montant
            curseur.execute("UPDATE comptes SET Solde = ? WHERE NumeroCompte = ?", (nouveauSolde, nocompte))
            curseur.execute("INSERT INTO operations (DateOperation, NumeroCompte, LibelleOperation, Montant) VALUES (DATE('NOW'), ?, ?, ?)", (nocompte, "Retrait", -montant))
            baseDeDonnees.commit()
            baseDeDonnees.close()
            return True

    def transfert(self, nocompteSource, nocompteDestination, montant):
        baseDeDonnees, curseur = self.connexionBaseDeDonnees()
        montant = float(montant)
        soldeCompteSource = self.solde(nocompteSource)
        if soldeCompteSource < montant or montant <= 0:
            baseDeDonnees.close()
            return False
        else:
            nouveauSoldeSource = soldeCompteSource - montant
            curseur.execute("UPDATE comptes SET Solde = ? WHERE NumeroCompte = ?", (nouveauSoldeSource, nocompteSource))
            curseur.execute("INSERT INTO operations (DateOperation, NumeroCompte, LibelleOperation, Montant) VALUES (DATE('NOW'), ?, ?, ?)", (nocompteSource, "Virement", -montant))
            soldeCompteDestination = self.solde(nocompteDestination)
            nouveauSoldeDestination = soldeCompteDestination + montant
            curseur.execute("UPDATE comptes SET Solde = ? WHERE NumeroCompte = ?", (nouveauSoldeDestination, nocompteDestination))
            curseur.execute("INSERT INTO operations (DateOperation, NumeroCompte, LibelleOperation, Montant) VALUES (DATE('NOW'), ?, ?, ?)", (nocompteDestination, "Virement", montant))
            baseDeDonnees.commit()
            baseDeDonnees.close()
            return True

    def depot(self, nocompte, montant):
        baseDeDonnees, curseur = self.connexionBaseDeDonnees()
        montant = float(montant)
        soldeCompte = self.solde(nocompte)
        nouveauSolde = soldeCompte + montant
        curseur.execute("UPDATE comptes SET Solde = ? WHERE NumeroCompte = ?", (nouveauSolde, nocompte))
        curseur.execute("INSERT INTO operations (DateOperation, NumeroCompte, LibelleOperation, Montant) VALUES (DATE('NOW'), ?, ?, ?)", (nocompte, "Dépôt", montant))
        baseDeDonnees.commit()
        baseDeDonnees.close()
        return True

    def historique(self, nocompte):
        baseDeDonnees, curseur = self.connexionBaseDeDonnees()
        curseur.execute("SELECT DateOperation, LibelleOperation, Montant FROM operations WHERE NumeroCompte = ? ORDER BY DateOperation DESC LIMIT 10;", (nocompte,))
        historiqueCSV = "\"DateOperation\";\"LibelleOperation\";\"Montant\"\n"
        for ligne in curseur.fetchall():
            historiqueCSV += "\"" + ligne[0] + "\";\"" + ligne[1] + "\";\"" + str(ligne[2]) + "\"\n"
        baseDeDonnees.close()
        return historiqueCSV

    def stop(self):
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        self.signals.stopped.emit()
        self.signals.update_status_label.emit("Server stopped")
        print("Server stopped")

class ClientThread(QThread):
    def __init__(self, server_address, port, signals):
        super().__init__()
        self.server_address = server_address
        self.port = port
        self.clientTLS = None
        self.signals = signals

    def run(self):
        try:
            context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile="server_cert.pem")
            context.check_hostname = False

            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.clientTLS = context.wrap_socket(client, server_hostname=self.server_address)
            self.clientTLS.connect((self.server_address, self.port))

            self.signals.connectedClient.emit(self.clientTLS)
        except Exception as e:
            self.signals.error.emit(f"Error connecting to the server: {e}")

    def send_message(self, message):
        try:
            if self.clientTLS:
                self.clientTLS.send(message.encode("utf-8"))
                response = self.clientTLS.recv(1024).decode("utf-8")
                self.signals.response_received.emit(response)
            else:
                self.signals.error.emit("Client not connected")
        except Exception as e:
            self.signals.error.emit(f"Error sending message: {e}")

    def close_connection(self):
        try:
            if self.clientTLS:
                self.clientTLS.close()
                self.signals.stoppedClient.emit()
        except Exception as e:
            self.signals.error.emit(f"Error closing connection: {e}")


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.server_thread = None
        self.client_thread = None

        self.signals = ServerSignals()

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.ui.widget_logo.hide()
        self.ui.stackedWidget.setCurrentIndex(0)
        self.ui.server_button.setChecked(True)

        # Connect buttons to their functions
        self.ui.server_button.clicked.connect(self.server_button)
        self.ui.server_button0.clicked.connect(self.server_button0)
        self.ui.client_btn.clicked.connect(self.client_btn)
        self.ui.client_btn0.clicked.connect(self.client_btn0)
        self.ui.account_btn.clicked.connect(self.account_btn)
        self.ui.account_btn0.clicked.connect(self.account_btn0)
        self.ui.operation_btn.clicked.connect(self.operation_btn)
        self.ui.operation_btn0.clicked.connect(self.operation_btn0)
        self.ui.pushButton.clicked.connect(self.pushButton)
        self.ui.pushButton0.clicked.connect(self.pushButton0)

        # Input Place holder Text
        self.ui.server_status_label.setText("Server status: Stopped")
        self.ui.port_input.setPlaceholderText("Enter the server port number (e.g., 8000)")

        self.ui.cert_input.setPlaceholderText("Path to certificate file (*.pem, *.crt)")
        self.ui.key_input.setPlaceholderText("Path to private key file (*.pem, *.key)")
        self.ui.message.setPlaceholderText("The first thing connect server then connect client server")

        # CSV upload buttons
        self.ui.Upload_client.clicked.connect(self.upload_clients)
        self.ui.Upload_account.clicked.connect(self.upload_accounts)
        self.ui.Upload_operations.clicked.connect(self.upload_operations)

        # SQLite database
        self.conn = sqlite3.connect('banque.db')
        self.create_tables()
        self.import_data_from_db("banque.db")

        # Connect upload buttons for certificates and keys
        self.ui.upload_cert.clicked.connect(self.upload_cert)
        self.ui.upload_key.clicked.connect(self.upload_key)

        # Connecter la fonction operation_selected à l'événement de changement de sélection du QComboBox
        self.ui.comboBox.addItems(["Choose","Deposit", "Withdrawal", "Transfer", "History", "balance"])
        self.ui.comboBox.currentIndexChanged.connect(self.operation_selected)
        self.ui.connect_to_server.clicked.connect(self.connect_button_clicked)
        self.ui.Stop_client_server.clicked.connect(self.stop_client)
        self.ui.start_server.clicked.connect(self.start_server)
        self.ui.connect_client.clicked.connect(self.connect_and_check_account)
        self.ui.stop_server.clicked.connect(self.stop_server)

        # Connect signals to slots
        self.signals.started.connect(self.on_server_started)
        self.signals.stopped.connect(self.on_server_stopped)
        self.signals.update_status_label.connect(self.update_status_label)
        self.signals.connectedClient.connect(self.on_connected)
        self.signals.stoppedClient.connect(self.on_client_stopped)
        self.signals.error.connect(self.on_error)

        # Open website
        self.ui.github.clicked.connect(self.open_website)
    #fonction for openning web site
    def open_website(self):
        url = QUrl("https://github.com/Aminelaakroute")
        QDesktopServices.openUrl(url)

    ## functions for changing menu page
    def server_button(self):
        self.ui.stackedWidget.setCurrentIndex(0)

    def server_button0(self):
        self.ui.stackedWidget.setCurrentIndex(0)

    def client_btn(self):
        self.ui.stackedWidget.setCurrentIndex(1)

    def client_btn0(self):
        self.ui.stackedWidget.setCurrentIndex(1)

    def account_btn(self):
        self.ui.stackedWidget.setCurrentIndex(2)

    def account_btn0(self):
        self.ui.stackedWidget.setCurrentIndex(2)

    def operation_btn(self):
        self.ui.stackedWidget.setCurrentIndex(3)

    def operation_btn0(self):
        self.ui.stackedWidget.setCurrentIndex(3)

    def pushButton(self):
        self.ui.stackedWidget.setCurrentIndex(4)

    def pushButton0(self):
        self.ui.stackedWidget.setCurrentIndex(4)

    ## Functions for displaying messages
    def display_success_message(self, success_message, text_edit_name):
        text_edit = getattr(self.ui, text_edit_name)
        text_edit.clear()
        text_edit.setStyleSheet("color: green")
        text_edit.setPlainText(success_message)

    def display_error_message(self, error_message, text_edit_name):
        text_edit = getattr(self.ui, text_edit_name)
        text_edit.clear()
        text_edit.setStyleSheet("color: red")
        text_edit.setPlainText(error_message)

    ## Function to upload clients CSV
    @pyqtSlot()
    def upload_clients(self):
        options = QFileDialog.Options()
        fileName, _ = QFileDialog.getOpenFileName(self, "Upload Clients CSV", "",
                                                  "CSV Files (*.csv);;All Files (*)", options=options)
        if fileName:
            try:
                clients_df = pd.read_csv(fileName, delimiter=';')
                self.insert_clients_into_db(clients_df, self.ui.textEdit)
                self.display_data_in_table(self.ui.clients_table, clients_df)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load CSV file: {e}")

    ## Function to upload accounts CSV
    @pyqtSlot()
    def upload_accounts(self):
        options = QFileDialog.Options()
        fileName, _ = QFileDialog.getOpenFileName(self, "Upload Accounts CSV", "",
                                                  "CSV Files (*.csv);;All Files (*)", options=options)
        if fileName:
            try:
                accounts_df = pd.read_csv(fileName, delimiter=';')
                self.insert_accounts_into_db(accounts_df, self.ui.textEdit_2)
                self.display_data_in_table(self.ui.account_table, accounts_df)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load CSV file: {e}")

    ## Function to upload operations CSV
    @pyqtSlot()
    def upload_operations(self):
        options = QFileDialog.Options()
        fileName, _ = QFileDialog.getOpenFileName(self, "Upload Accounts CSV", "",
                                                  "CSV Files (*.csv);;All Files (*)", options=options)
        if fileName:
            try:
                operations_df = pd.read_csv(fileName, delimiter=';')
                self.insert_operations_into_db(operations_df, self.ui.textEdit_3)
                self.display_data_in_table(self.ui.Operation_table, operations_df)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load CSV file: {e}")

    def insert_clients_into_db(self, dataframe, textEdit):
        try:
            cursor = self.conn.cursor()
            cursor.execute('DELETE FROM clients')  # Clear existing data
            for index, row in dataframe.iterrows():
                cursor.execute('''
                    INSERT INTO clients (NumeroClient, Nom, Prenom, Adresse, CodePostal, Ville, TelephoneFixe, TelephonePortable) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                row['NumeroClient'], row['Nom'], row['Prenom'], row['Adresse'], row['CodePostal'], row['Ville'],
                row['TelephoneFixe'], row['TelephonePortable']))
            self.conn.commit()
            success_message = "Clients data inserted successfully!"
            self.display_success_message(success_message, "textEdit")
        except sqlite3.Error as e:
            error_message = f"Failed to insert clients data: {e}"
            self.display_error_message(error_message, "textEdit")

    def insert_accounts_into_db(self, dataframe, textEdit_2):
        try:
            cursor = self.conn.cursor()
            cursor.execute('DELETE FROM comptes')  # Clear existing data
            for index, row in dataframe.iterrows():
                cursor.execute('''
                    INSERT INTO comptes (NumeroCompte, NumeroClient, TypeCompte, PIN, Solde ) 
                    VALUES (?, ?, ?, ?, ?)
                ''', (row['NumeroCompte'], row['NumeroClient'], row['TypeCompte'], row['PIN'], row['Solde']))
            self.conn.commit()
            success_message = "Accounts data inserted successfully!"
            self.display_success_message(success_message, "textEdit_2")
        except sqlite3.Error as e:
            error_message = f"Failed to insert accounts data: {e}"
            self.display_error_message(error_message, "textEdit_2")

    def insert_operations_into_db(self, dataframe, textEdit_3):
        try:
            cursor = self.conn.cursor()
            cursor.execute('DELETE FROM Operations')  # Clear existing data
            for index, row in dataframe.iterrows():
                cursor.execute('''
                    INSERT INTO operations (NumeroOperation, DateOperation, NumeroCompte, LibelleOperation, Montant) 
                    VALUES (?, ?, ?, ?, ?)
                ''', (row['NumeroOperation'], row['DateOperation'], row['NumeroCompte'], row['LibelleOperation'],
                      row['Montant']))
            self.conn.commit()
            success_message = "Operations data inserted successfully!"
            self.display_success_message(success_message, "textEdit_3")
        except sqlite3.Error as e:
            error_message = f"Failed to insert operations data: {e}"
            self.display_error_message(error_message, "textEdit_3")

    def display_data_in_table(self, table, dataframe):
        table.setRowCount(0)
        table.setColumnCount(dataframe.shape[1])
        table.setHorizontalHeaderLabels(dataframe.columns)

        for row_idx in range(dataframe.shape[0]):
            table.insertRow(row_idx)
            for col_idx in range(dataframe.shape[1]):
                table.setItem(row_idx, col_idx, QTableWidgetItem(str(dataframe.iat[row_idx, col_idx])))

    def import_data_from_db(self, db_name):
        try:
            # Essayer d'établir une connexion à la base de données
            conn = sqlite3.connect(db_name)
            # Vérifier si la base de données est vide
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM clients")
            row_count = cursor.fetchone()[0]
            if row_count == 0:
                # La base de données est vide, ne pas exécuter la méthode
                return
            # Récupérer les données clients depuis la base de données
            clients_query = "SELECT * FROM clients"
            clients_df = pd.read_sql_query(clients_query, conn)
            # Afficher les données dans la table des clients
            self.display_data_in_table(self.ui.clients_table, clients_df)
            # Récupérer les données des comptes depuis la base de données
            accounts_query = "SELECT * FROM comptes"
            accounts_df = pd.read_sql_query(accounts_query, conn)
            # Afficher les données dans la table des comptes
            self.display_data_in_table(self.ui.account_table, accounts_df)
            # Récupérer les données des opérations depuis la base de données
            operations_query = "SELECT * FROM operations"
            operations_df = pd.read_sql_query(operations_query, conn)
            # Afficher les données dans la table des opérations
            self.display_data_in_table(self.ui.Operation_table, operations_df)
            # Afficher un message de succès dans le QTextEdit
            success_message = "Data imported successfully!"
            self.display_success_message(success_message, "textEdit")

        except sqlite3.Error as e:
            # La base de données n'existe pas ou une erreur est survenue lors de la connexion
            error_message = f"Failed to import data from database: {e}"
            self.display_error_message(error_message, "textEdit")

        finally:
            if conn:
                conn.close()

    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clients (
                NumeroClient INTEGER PRIMARY KEY AUTOINCREMENT,
                Nom TEXT NOT NULL, 
                Prenom TEXT NOT NULL, 
                Adresse TEXT, 
                CodePostal TEXT, 
                Ville TEXT, 
                TelephoneFixe TEXT, 
                TelephonePortable TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS comptes (
                NumeroCompte INTEGER PRIMARY KEY AUTOINCREMENT, 
                NumeroClient INTEGER NOT NULL, 
                TypeCompte TEXT NOT NULL, 
                PIN TEXT NOT NULL, 
                Solde REAL, 
                FOREIGN KEY (NumeroClient) REFERENCES Clients(NumeroClient)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS operations (
                NumeroOperation INTEGER PRIMARY KEY AUTOINCREMENT, 
                DateOperation TEXT NOT NULL, 
                NumeroCompte INTEGER NOT NULL, 
                LibelleOperation TEXT NOT NULL, 
                Montant REAL, 
                FOREIGN KEY (NumeroCompte) REFERENCES Comptes(NumeroCompte)
            )
        ''')
        self.conn.commit()

    @pyqtSlot()
    def upload_cert(self):
        options = QFileDialog.Options()
        fileName, _ = QFileDialog.getOpenFileName(self, "Upload Certificate", "",
                                                  "Certificate Files (*.pem *.crt);;All Files (*)", options=options)
        if fileName:
            self.ui.cert_input.setText(fileName)

    @pyqtSlot()
    def upload_key(self):
        options = QFileDialog.Options()
        fileName, _ = QFileDialog.getOpenFileName(self, "Upload Key", "",
                                                  "Key Files (*.pem *.key);;All Files (*)", options=options)
        if fileName:
            self.ui.key_input.setText(fileName)

    def start_server(self):
        if self.server_thread and self.server_thread.is_alive():
            QMessageBox.warning(self, "Warning", "Server is already running!")
            return

        try:
            port = int(self.ui.port_input.text())
            server_cert = self.ui.cert_input.text()
            server_key = self.ui.key_input.text()
            server_address = '127.0.0.1'

            if not server_cert or not server_key:
                QMessageBox.critical(self, "Error", "Certificate and key files must be specified.")
                return

            self.server_thread = ServerThread(port, server_address, server_cert, server_key, self.signals)
            self.server_thread.start()
            print("Server thread started.")

        except ValueError:
            QMessageBox.critical(self, "Error", "Port must be an integer.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to start server: {e}")
            print(f"Failed to start server: {e}")

    def on_server_started(self, port):
        self.ui.server_status_label.setText(f"Server started on port {port}")

    def stop_server(self):
        if not self.server_thread or not self.server_thread.is_alive():
            QMessageBox.warning(self, "Warning", "Server is not running!")
            return
        self.server_thread.stop()
        self.server_thread.join()  # Ensure the thread stops completely
        print("Server thread stopped.")

    def on_server_stopped(self):
        self.ui.server_status_label.setText("Server stopped")

    @pyqtSlot(str)
    def update_status_label(self, message):
        self.ui.server_status_label.setText(message)

    @pyqtSlot()
    def connect_button_clicked(self):
        try:
            server_address = '127.0.0.1'
            port = int(self.ui.port_input.text())

            # Vérifier si le ServerThread est en cours d'exécution
            if not self.server_thread or not self.server_thread.is_alive():
                self.on_error("Le serveur n'est pas en cours d'exécution.")
                self.ui.server_status_label.setText("Le serveur n'est pas en cours d'exécution.")
                return

            self.client_thread = ClientThread(server_address, port, self.signals)
            self.client_thread.start()
        except ValueError:
            self.on_error("Server port must be an integer.")
        except Exception as e:
            self.on_error(f"Error connecting to the server: {e}")

    def stop_client(self):
        if not self.client_thread : #or not self.client_thread.signals.isRunning():
            QMessageBox.warning(self, "Warning", "Client is not running!")
            return
        self.client_thread.close_connection()

    def on_client_stopped(self):
        self.ui.server_status_label.setText("Client stopped")

    @pyqtSlot(object)
    def on_connected(self, client_socket):
        self.ui.server_status_label.setText(
            f"Connected to server at 127.0.0.1:{self.ui.port_input.text()}")
        # Utilisez le socket client ici

    @pyqtSlot(str)
    def on_error(self, error_message):
        QMessageBox.critical(self, "Error", error_message)

    def connect_and_check_account(self):
        try:
            server_address = '127.0.0.1'
            port = int(self.ui.port_input.text())
            nocompte = self.ui.edit_compte.text()
            pin = self.ui.edit_pin.text()

            self.client_thread = ClientThread(server_address, port, self.signals)
            self.client_thread.signals.connectedClient.connect(lambda clientTLS: self.check_account_wrapper(clientTLS, nocompte, pin))
            self.client_thread.signals.error.connect(self.on_error5)
            self.client_thread.start()
        except Exception as e:
            QMessageBox.critical(self, "Warning", "Le serveur n'est pas connecté")
            print(f"Error: le serveur n'est pas connecté {e}")

    def check_account_wrapper(self, clientTLS, nocompte, pin):
        if self.check_account(clientTLS, nocompte, pin):
            self.on_connected5(clientTLS)
        else:
            clientTLS.close()

    def check_account(self, clientTLS, nocompte, pin):
        try:
            clientTLS.send(f"TESTPIN {nocompte} {pin}".encode("utf-8"))
            response = clientTLS.recv(255).decode("utf-8")

            if response == "TESTPIN OK":
                print("Account verified.")
                self.ui.message.setText("Account verified")
                return True
            else:
                print("Incorrect account number or PIN.")
                self.ui.message.setText("Incorrect account number or PIN.")
                return False

        except Exception as e:
            print(f"Error checking account: {e}")
            self.ui.message.setText(f"Error checking account: {e}")
            return False

    def on_connected5(self, clientTLS):
        print("Successfully connected and verified.")
        # Vous pouvez ajouter ici des actions supplémentaires à effectuer après la connexion et la vérification réussie.

    def on_error5(self, error_message):
        print(error_message)

    def operation_selected(self, index):
        selected_operation = self.ui.comboBox.currentText()
        if selected_operation == "Deposit":
            self.depot_Client()
        elif selected_operation == "Withdrawal":
            self.retrait_Client()
        elif selected_operation == "Transfer":
            self.transfert_Client()
        elif selected_operation == "History":
            self.historique_Client()
        elif selected_operation == "balance":
            self.solde_Client()

    def depot_Client(self):
        montant, ok = QInputDialog.getDouble(self, 'Dépôt', 'Entrez le montant à déposer:')
        if ok:
            self.connect_and_execute("DEPOT", montant)

    def retrait_Client(self):
        montant, ok = QInputDialog.getDouble(self, 'Retrait', 'Entrez le montant à retirer:')
        if ok:
            montant *= -1  # Convertir en valeur négative
            self.connect_and_execute("RETRAIT", montant)

    def transfert_Client(self):
        montant, ok = QInputDialog.getDouble(self, 'Transfert', 'Entrez le montant à transférer:')
        if ok:
            destcompte, ok = QInputDialog.getText(self, 'Transfert', 'Entrez le numéro de compte destinataire:')
            if ok:
                self.connect_and_execute("TRANSFERT", montant, destcompte)

    def historique_Client(self):
        self.connect_and_execute("HISTORIQUE")

    def solde_Client(self):
        self.connect_and_execute("SOLDE")

    def connect_and_execute(self, operation, montant=None, destcompte=None):
        server_address = '127.0.0.1'
        port = int(self.ui.port_input.text())
        nocompte = self.ui.edit_compte.text()
        pin = self.ui.edit_pin.text()

        self.client_thread = ClientThread(server_address, port, self.signals)
        self.client_thread.connectedClient.connect(
            lambda clientTLS: self.check_account_and_execute(clientTLS, operation, nocompte, pin, montant, destcompte))
        self.client_thread.error.connect(self.on_error)
        self.client_thread.start()

    def check_account_and_execute(self, clientTLS, operation, nocompte, pin, montant=None, destcompte=None):
        self.client_thread.response_received.connect(
            lambda response: self.handle_check_account_response(response, operation, nocompte, pin, montant, destcompte))
        self.client_thread.send_message(f"TESTPIN {nocompte} {pin}")

    def handle_check_account_response(self, response, operation, nocompte, pin, montant=None, destcompte=None):
        if response == "TESTPIN OK":
            print("Account verified.")
            self.execute_operation(operation, nocompte, montant, destcompte)
        else:
            print("Account verification failed.")

    def execute_operation(self, operation, nocompte, montant=None, destcompte=None):
        message = None
        if operation == "DEPOT":
            message = f"DEPOT {nocompte} {montant}"
        elif operation == "RETRAIT":
            message = f"RETRAIT {nocompte} {montant}"
        elif operation == "TRANSFERT":
            message = f"TRANSFERT {nocompte} {destcompte} {montant}"
        elif operation == "HISTORIQUE":
            message = f"HISTORIQUE {nocompte}"
        elif operation == "SOLDE":
            message = f"SOLDE {nocompte}"

        if message:
            self.client_thread.response_received.disconnect()  # Déconnecter les anciens signaux
            self.client_thread.response_received.connect(self.display_response)
            self.client_thread.send_message(message)

    def display_response(self, response):
        print(f"Response from server: {response}")
        self.ui.message.setText(f"Response from server: {response}")
        self.client_thread.close_connection()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())