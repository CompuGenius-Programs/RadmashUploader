import json
import os
import sys
from datetime import datetime

import requests
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, \
    QPushButton, QFileDialog, QMessageBox, QComboBox, QProgressDialog
from convertdate import hebrew
from titlecase import titlecase

SERVER_URL_CONFIG_KEY = 'SERVER_URL'
FILE_FILTER = "Divrei Torah (*.pdf)"
FILE_CONTENT_TYPE = 'application/pdf'

parshas_url = "https://github.com/CompuGenius-Programs/RadmashUploader/blob/main/parshas.json"
parshas = requests.get(parshas_url).json()["parshas"]


class FileEntryWidget(QWidget):
    def __init__(self, file_path, main_window):
        super().__init__()

        self.file_path = file_path
        self.main_window = main_window

        self.file_label = QLabel()
        self.file_label.setText(file_path.split("/")[-1])

        self.title_entry = QLineEdit()

        filename = self.file_label.text()
        # if filename.startswith("Kaarah"):
        #     volume = titlecase(filename.removeprefix('Kaarah ').removesuffix('.pdf'))
        #     title = f"Volume {volume}"
        # else:
        #     now = datetime.now()
        #     year = now.year
        #     month = now.month
        #     day = now.day
        #
        #     filename = filename.removesuffix(".pdf").replace(" dvar Torah ", "")
        #     if str(year) in filename:
        #         title = filename.replace(str(year), "") + " " + str(hebrew.from_gregorian(year, month, day)[0])
        #     else:
        #         title = filename[:-4]

        # self.title_entry.setText(titlecase(title))

        self.parsha_dropdown = QComboBox()
        self.parsha_dropdown.addItems(parshas)
        for parsha in parshas:
            if (parsha.lower() in filename.lower() and
                    ((parsha.lower() + ' ') in filename.lower() or(parsha.lower() + '_') in filename.lower())):
                self.parsha_dropdown.setCurrentText(parsha)
                break

        self.year_input = QLineEdit()
        if '20' in filename:
            try:
                gregorian_year = filename.split('20')[-1].split('.')[0]
                file_creation_date = datetime.fromtimestamp(os.path.getctime(file_path))
                year = str(hebrew.from_gregorian(
                    int('20' + gregorian_year), file_creation_date.month, file_creation_date.day)[0])
            except ValueError:
                year = ''
        else:
            year = '57' + filename.split('57')[-1].split('.')[0]
        self.year_input.setText(year)

        self.remove_button = QPushButton("Remove")
        self.remove_button.clicked.connect(self.remove_self)

        file_layout = QHBoxLayout()
        file_layout.addWidget(self.file_label)
        file_layout.addWidget(self.remove_button)

        entry_layout = QHBoxLayout()
        # entry_layout.addWidget(QLabel("Title:"))
        # entry_layout.addWidget(self.title_entry)
        entry_layout.addWidget(QLabel("Parsha:"))
        entry_layout.addWidget(self.parsha_dropdown)
        entry_layout.addWidget(QLabel("Hebrew Year:"))
        entry_layout.addWidget(self.year_input)

        layout = QVBoxLayout()
        layout.addLayout(file_layout)
        layout.addLayout(entry_layout)

        self.setLayout(layout)

    def remove_self(self):
        self.main_window.remove_file_entry(self)
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
                default_server_url = config.get(SERVER_URL_CONFIG_KEY)
        except (FileNotFoundError, json.decoder.JSONDecodeError):
            default_server_url = ""

        if default_server_url:
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
        file_dialog.setNameFilter(FILE_FILTER)
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

    def handle_upload_response(self, response):
        if response.status_code == 200:
            QMessageBox.information(self, "Success", "Files uploaded successfully")
        else:
            QMessageBox.critical(self, "Error", f"Error uploading files: {response.text}")

    def upload_files(self):
        server_url = self.server_url_entry.text()
        if not server_url:
            QMessageBox.warning(self, "Warning", "Please enter a server URL")
            return

        progress = QProgressDialog("Uploading files...", None, 0, 0, self)
        try:
            response = requests.post(server_url + '/upload', files=self.get_files_payload(),
                                     data=self.get_data_payload())
            self.handle_upload_response(response)
        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "Error", str(e))
        progress.close()

    def get_files_payload(self):
        files = []
        for file_entry in self.file_entries:
            file_path = file_entry.file_path
            file_name = (file_entry.parsha_dropdown.currentText().lower().replace(' ', '_') +
                         "_" + file_entry.year_input.text() + ".pdf")
            # file_name = file_path.split("/")[-1]
            with open(file_path, 'rb') as file:
                file_content = file.read()
                files.append(('file', (file_name, file_content, FILE_CONTENT_TYPE)))
        return files

    def get_data_payload(self):
        data = {}
        for i, file_entry in enumerate(self.file_entries):
            parsha = file_entry.parsha_dropdown.currentText()
            year = file_entry.year_input.text()
            if not parsha or not year:
                QMessageBox.warning(self, "Warning", "Please enter a parsha and year for all files")
                return {}
            data[f'title_{i + 1}'] = titlecase(parsha + " " + year)
        return data


if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())
