import sys

import requests
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, \
    QPushButton, QFileDialog, QMessageBox


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

        layout = QHBoxLayout()
        layout.addWidget(self.file_label)
        layout.addWidget(self.title_entry)
        layout.addWidget(self.remove_button)

        self.setLayout(layout)

    def remove_self(self):
        self.main_window.remove_file_entry(self)  # Notify the main window to remove this entry
        self.setParent(None)
        self.deleteLater()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.file_entries = []

        self.setWindowTitle("File Upload")
        self.resize(400, 300)

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)

        self.select_button = QPushButton("Select Files")
        self.select_button.clicked.connect(self.select_files)

        self.files_layout = QVBoxLayout()

        self.submit_button = QPushButton("Submit")
        self.submit_button.clicked.connect(self.upload_files)

        main_layout.addWidget(self.select_button)
        main_layout.addLayout(self.files_layout)
        main_layout.addWidget(self.submit_button)

    def select_files(self):
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.ExistingFiles)
        file_dialog.setNameFilter("PDF Files (*.pdf)")
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
        file_entries_data = []
        files = []
        for file_entry in self.file_entries:
            file_path = file_entry.file_path
            file_name = file_path.split("/")[-1]
            title = file_entry.title_entry.text()
            file_entries_data.append((file_path, file_name, title))
            with open(file_path, 'rb') as file:
                file_content = file.read()
                files.append(('file', (file_name, file_content, 'application/pdf')))

        data = {f'title_{i + 1}': title for i, (_, _, title) in enumerate(file_entries_data)}

        response = requests.post('http://localhost:8080/upload', files=files, data=data)

        if response.status_code == 200:
            QMessageBox.information(self, "Success", "Files uploaded successfully")
        else:
            QMessageBox.critical(self, "Error", f"Error uploading files: {response.text}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())
