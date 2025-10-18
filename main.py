import sys
from PyQt6.QtWidgets import QApplication
from db_manager import DatabaseManager
from main_gui import LoginWindow

def main():
    app = QApplication(sys.argv)
    dbm = DatabaseManager()
    login = LoginWindow(dbm)
    login.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
