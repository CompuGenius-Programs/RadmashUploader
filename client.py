import sys

import requests
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, \
    QPushButton, QFileDialog, QMessageBox
import json


class FileEntryWidget(QWidget):
    def __init__(self, file_path, main_window):
        super().__init__()

        self.file_path = file_path
        self.main_window = main_window

        self.file_label = QLabel()
        self.file_label.setText(file_path.split("/")[-1])

        self.title_entry = QLineEdit()

        self.remove_button = QPushButton("Remove")
        self.remove_button.clicked.connect(self.remove_self)

        file_layout = QHBoxLayout()
        file_layout.addWidget(self.file_label)
        file_layout.addWidget(self.remove_button)

        entry_layout = QHBoxLayout()
        entry_layout.addWidget(QLabel("Title:"))
        entry_layout.addWidget(self.title_entry)

        layout = QVBoxLayout()
        layout.addLayout(file_layout)
        layout.addLayout(entry_layout)

        self.setLayout(layout)

    def remove_self(self):
        self.main_window.remove_file_entry(self)  # Notify the main window to remove this entry
        self.setParent(None)
        self.deleteLater()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.file_entries = []

        self.setWindowTitle("Radmash Uploader")
        self.resize(400, 300)

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)

        server_url_layout = QHBoxLayout()
        self.server_url_label = QLabel("Server URL (don't change unless necessary):")
        self.server_url_entry = QLineEdit()
        self.server_url_entry.mouseDoubleClickEvent = self.toggle_editable

        try:
            with open('config.json') as config_file:
                config = json.load(config_file)
                default_server_url = config.get('SERVER_URL')
        except (FileNotFoundError, json.decoder.JSONDecodeError):
            default_server_url = ""

        if default_server_url != "":
            self.server_url_entry.setReadOnly(True)

        self.server_url_entry.setText(default_server_url)
        server_url_layout.addWidget(self.server_url_label)
        server_url_layout.addWidget(self.server_url_entry)

        self.select_button = QPushButton("Select Files")
        self.select_button.clicked.connect(self.select_files)

        self.files_layout = QVBoxLayout()

        self.submit_button = QPushButton("Submit")
        self.submit_button.clicked.connect(self.upload_files)

        main_layout.addLayout(server_url_layout)
        main_layout.addWidget(self.select_button)
        main_layout.addLayout(self.files_layout)
        main_layout.addWidget(self.submit_button)

    def toggle_editable(self, event):
        self.server_url_entry.setReadOnly(False)

    def select_files(self):
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.ExistingFiles)
        file_dialog.setNameFilter("Divrei Torah (*.pdf)")
        if file_dialog.exec_():
            file_paths = file_dialog.selectedFiles()
            for file_path in file_paths:
                self.add_file_entry(file_path)

    def add_file_entry(self, file_path):
        file_entry_widget = FileEntryWidget(file_path, self)
        self.files_layout.addWidget(file_entry_widget)
        self.file_entries.append(file_entry_widget)

    def remove_file_entry(self, file_entry):
        self.file_entries.remove(file_entry)

    def upload_files(self):
        server_url = self.server_url_entry.text()  # Get the server URL from the input field
        if not server_url:
            QMessageBox.warning(self, "Warning", "Please enter a server URL")
            return

        file_entries_data = []
        files = []
        empty_fields = False  # Flag to track if any input field is empty

        for file_entry in self.file_entries:
            file_path = file_entry.file_path
            file_name = file_path.split("/")[-1]
            title = file_entry.title_entry.text()

            if not title:  # Check if the title field is empty
                empty_fields = True
                QMessageBox.warning(self, "Warning", "Please enter a title for all files")
                break

            file_entries_data.append((file_path, file_name, title))
            with open(file_path, 'rb') as file:
                file_content = file.read()
                files.append(('file', (file_name, file_content, 'application/pdf')))

        if empty_fields:
            return

        data = {f'title_{i + 1}': title for i, (_, _, title) in enumerate(file_entries_data)}

        response = requests.post(server_url + '/upload', files=files, data=data)

        if response.status_code == 200:
            QMessageBox.information(self, "Success", "Files uploaded successfully")
        else:
            QMessageBox.critical(self, "Error", f"Error uploading files: {response.text}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())
