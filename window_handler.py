
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QLabel, QLineEdit, QVBoxLayout
from PyQt5.QtCore import Qt
import sys
import user_handler

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MTG Sorter")
        self.setGeometry(2000, 100, 300, 300)
        self.initUI()
        self.showMaximized()
    
    def initUI(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        title = QLabel("MTG Sorter", self)
        username_label = QLabel("Username:", self)
        self.username_field = QLineEdit(self)
        card_code_label = QLabel("Card Code:", self)
        self.card_code_field = QLineEdit(self)
        self.sign_in_button = QtWidgets.QPushButton("Sign In", self)

        title.setStyleSheet("color: white; font-size: 48px;")
        username_label.setStyleSheet("font-size: 24px;")
        self.username_field.setStyleSheet("font-size: 24px;")
        card_code_label.setStyleSheet("font-size: 24px;")
        self.card_code_field.setStyleSheet("font-size: 24px;")
        self.sign_in_button.setStyleSheet("font-size: 24px;")

        title.setAlignment(Qt.AlignHCenter)
        username_label.setAlignment(Qt.AlignHCenter)
        self.username_field.setAlignment(Qt.AlignCenter)
        card_code_label.setAlignment(Qt.AlignHCenter)
        self.card_code_field.setAlignment(Qt.AlignCenter)

        self.sign_in_button.clicked.connect(self.sign_in)

        vbox = QVBoxLayout()
        vbox.addWidget(title)
        vbox.addWidget(username_label)
        vbox.addWidget(self.username_field)
        vbox.addWidget(card_code_label)
        vbox.addWidget(self.card_code_field)
        vbox.addWidget(self.sign_in_button)
        central_widget.setLayout(vbox)

    def sign_in(self):
        if user_handler.check_login(self.username_field.text(), self.card_code_field.text()):
            self.sign_in_button.setStyleSheet("background-color: green; font-size: 24px;")

def gui():
    # Start app and create window
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()

    sys.exit(app.exec_())

if __name__ == "__main__":
    gui()