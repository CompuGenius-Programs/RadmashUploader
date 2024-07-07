import json
import os
import sys
from datetime import datetime

import requests
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, \
    QPushButton, QFileDialog, QMessageBox, QComboBox, QProgressDialog, QDialog, QTextEdit
from convertdate import hebrew
from titlecase import titlecase

SERVER_URL_CONFIG_KEY = 'SERVER_URL'
FILE_FILTER = "Divrei Torah (*.pdf)"
FILE_CONTENT_TYPE = 'application/pdf'

parshas_url = "https://raw.githubusercontent.com/CompuGenius-Programs/Radmash/main/parshas.json"
parshas = requests.get(parshas_url).json()["parshas"]


class UploadThread(QThread):
    finished = pyqtSignal(object)  # Signal to emit the response or exception

    def __init__(self, url, files, data):
        super().__init__()
        self.url = url
        self.files = files
        self.data = data

    def run(self):
        try:
            response = requests.post(self.url, files=self.files, data=self.data)
            self.finished.emit(response)
        except Exception as e:
            self.finished.emit(e)


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
            if (parsha.lower() in filename.lower() and (
                    (parsha.lower() + ' ') in filename.lower() or (parsha.lower() + '_') in filename.lower())):
                self.parsha_dropdown.setCurrentText(parsha)
                break

        self.year_input = QLineEdit()
        if '20' in filename:
            try:
                gregorian_year = filename.split('20')[-1].split('.')[0]
                file_creation_date = datetime.fromtimestamp(os.path.getctime(file_path))
                year = str(
                    hebrew.from_gregorian(int('20' + gregorian_year), file_creation_date.month, file_creation_date.day)[
                        0])
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


class ErrorDialog(QDialog):
    def __init__(self, parent=None, error_message="Error", detailed_text=""):
        super().__init__(parent)
        self.setWindowFlags(self.windowFlags() | Qt.WindowSystemMenuHint | Qt.WindowMaximizeButtonHint)
        self.setWindowTitle("Error")
        self.init_ui(error_message, detailed_text)

    def init_ui(self, error_message, detailed_text):
        layout = QVBoxLayout()

        error_label = QLabel(error_message)
        layout.addWidget(error_label)

        detailed_text_edit = QTextEdit()
        detailed_text_edit.setReadOnly(True)
        detailed_text_edit.setText(detailed_text)
        layout.addWidget(detailed_text_edit)

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)

        self.setLayout(layout)


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

        self.progress = None

        main_layout.addLayout(server_url_layout)
        main_layout.addWidget(self.select_button)
        main_layout.addLayout(self.files_layout)
        main_layout.addWidget(self.submit_button)

    def toggle_editable(self, event):
        self.server_url_entry.setReadOnly(False)

    def select_files(self):
        try:
            with open('config.json') as config_file:
                config = json.load(config_file)
                last_directory = config.get("LAST_DIRECTORY", "")
        except (FileNotFoundError, json.decoder.JSONDecodeError):
            last_directory = ""

        file_dialog = QFileDialog()
        file_dialog.setDirectory(last_directory)
        file_dialog.setFileMode(QFileDialog.ExistingFiles)
        file_dialog.setNameFilter(FILE_FILTER)
        if file_dialog.exec_():
            file_paths = file_dialog.selectedFiles()
            for file_path in file_paths:
                self.add_file_entry(file_path)

            if file_paths:
                selected_directory = os.path.dirname(file_paths[0])
                config["LAST_DIRECTORY"] = selected_directory
                with open('config.json', 'w') as config_file:
                    json.dump(config, config_file)

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

        self.progress = QProgressDialog("Uploading files...", None, 0, 0, self)
        self.progress.setWindowFlags(
            self.progress.windowFlags() & ~(Qt.WindowCloseButtonHint | Qt.WindowContextHelpButtonHint))
        self.progress.setWindowTitle("Radmash Uploader")
        self.progress.show()

        self.upload_thread = UploadThread(server_url + '/upload', self.get_files_payload(), self.get_data_payload())
        self.upload_thread.finished.connect(self.handle_upload_response_thread)
        self.upload_thread.start()

    def handle_upload_response_thread(self, result):
        if isinstance(result, requests.Response) and result.status_code == 200:
            if result.status_code == 200:
                QMessageBox.information(self, "Success", "Files uploaded successfully")
            else:
                dialog = ErrorDialog(error_message="Error uploading files", detailed_text=result.text)
                dialog.exec_()
        else:
            dialog = ErrorDialog(error_message="Error uploading files", detailed_text=str(result))
            dialog.exec_()
        self.progress.close()

    def get_files_payload(self):
        files = []
        for file_entry in self.file_entries:
            file_path = file_entry.file_path
            file_name = (file_entry.parsha_dropdown.currentText().lower().replace(' ',
                                                                                  '_') + "_" + file_entry.year_input.text() + ".pdf")
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
