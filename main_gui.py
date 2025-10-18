import pickle
import gspread
import requests
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import os
from datetime import datetime, date
from dialogs import AddEditBookDialog,AddEditStudentDialog
from PyQt6.QtWidgets import (
    QWidget, QMainWindow, QMessageBox, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QStackedWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QGroupBox, QFormLayout, QComboBox, QDateEdit, QFileDialog,QProgressBar,QDialog,QApplication,QInputDialog
)
from PyQt6.QtCore import Qt, QDate, QTimer,pyqtSignal,QRunnable,QObject,QThreadPool
from PyQt6.QtGui import QIcon
from db_manager import DatabaseManager
import sys

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and PyInstaller."""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# GOOGLE AUTH & DRIVE FUNCTIONS

def get_user_gsheet_client():
    """Authenticate user with Google OAuth and return gspread client."""
    SCOPES = [
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/spreadsheets"
    ]
    
    DROPBOX_LINK = "https://www.dropbox.com/scl/fi/nhghxpmnefc2g45uba15h/credentials.json?rlkey=uqlgnm5lori28rpy8qx6hkuj5&st=8l76xdn6&dl=1"

    creds = None
    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            resp = requests.get(DROPBOX_LINK)
            if resp.status_code != 200:
                raise Exception(f"Failed to fetch credentials from Dropbox. Status: {resp.status_code}")
            creds_json = resp.json()
            
            flow = InstalledAppFlow.from_client_config(creds_json, SCOPES)
            creds = flow.run_local_server(port=0)

        with open("token.pickle", "wb") as token:
            pickle.dump(creds, token)

    return gspread.authorize(creds)

def google_login():
    """Force user to log in with Google and refresh credentials."""
    SCOPES = [
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/spreadsheets"
    ]
    DROPBOX_LINK = "https://www.dropbox.com/scl/fi/nhghxpmnefc2g45uba15h/credentials.json?rlkey=uqlgnm5lori28rpy8qx6hkuj5&st=8l76xdn6&dl=1"
    resp = requests.get(DROPBOX_LINK)
    if resp.status_code != 200:
        raise Exception(f"Failed to fetch credentials from Dropbox. Status: {resp.status_code}")
    creds_json = resp.json()
    flow = InstalledAppFlow.from_client_config(creds_json, SCOPES)
    creds = flow.run_local_server(port=0)
    with open("token.pickle", "wb") as token:
        pickle.dump(creds, token)
    return creds

def google_logout():
    """Logout Google by deleting local token."""
    if os.path.exists("token.pickle"):
        os.remove("token.pickle")
        return True
    return False

class WorkerSignals(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(str)
    success = pyqtSignal(str)

class DriveSyncWorker(QRunnable):
    def __init__(self, dbm):
        super().__init__()
        self.dbm = dbm
        self.signals = WorkerSignals()

    def run(self):
        try:
            export_to_user_drive(self.dbm)
            self.signals.success.emit("Library data synced to your Google Drive!")
        except Exception as e:
            self.signals.error.emit(str(e))
        finally:
            self.signals.finished.emit()

def export_to_user_drive(dbm):
    """Upload local SQLite data to user's Google Drive as Google Sheets."""
    client = get_user_gsheet_client()
    tables = ["books", "students", "issued_books", "users"]

    for table in tables:
        sheet_title = f"MyLibrary_{table}"
        try:
            sheet = client.open(sheet_title).sheet1
            sheet.clear()
        except gspread.SpreadsheetNotFound:
            sheet = client.create(sheet_title).sheet1

        c = dbm.conn.cursor()
        c.execute(f"SELECT * FROM {table}")
        rows = c.fetchall()

        if not rows:
            continue

        columns = [col[0] for col in c.description]
        sheet.append_row(columns)

        for row in rows:
            sheet.append_row(list(row))

    return True



# Login Window
class LoginWindow(QWidget):
    def __init__(self, dbm: DatabaseManager):
        super().__init__()
        self.dbm = dbm
        self.setWindowTitle("Library Tracker - Login")
        self.setWindowIcon(QIcon(resource_path("library.ico")))
        self.resize(360, 180)
        layout = QVBoxLayout()

        title = QLabel("<h2>Library Management</h2>")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        form = QFormLayout()
        self.username = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Username:", self.username)
        form.addRow("Password:", self.password)
        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        self.login_btn = QPushButton("Login")
        self.quit_btn = QPushButton("Quit")
        btn_layout.addWidget(self.login_btn)
        btn_layout.addWidget(self.quit_btn)
        layout.addLayout(btn_layout)

        help_label = QLabel("Default admin: admin / admin")
        help_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(help_label)

        self.setLayout(layout)

        self.login_btn.clicked.connect(self.try_login)
        self.quit_btn.clicked.connect(self.close)
        self.username.setText("admin")

    def try_login(self):
        u = self.username.text().strip()
        p = self.password.text().strip()
        if self.dbm.validate_user(u, p):
            self.open_main()
        else:
            QMessageBox.warning(self, "Login failed", "Invalid username or password.")

    def open_main(self):
        self.main = MainWindow(self.dbm)
        self.main.show()
        self.close()

# Main Application Window
class MainWindow(QMainWindow):
    def __init__(self, dbm: DatabaseManager):
        super().__init__()
        self.dbm = dbm
        self.setWindowTitle("Library Tracker - Dashboard")
        self.setWindowIcon(QIcon(resource_path("library.ico")))
        self.resize(1000, 650)
        central = QWidget()
        main_layout = QHBoxLayout()
        central.setLayout(main_layout)
        self.setCentralWidget(central)
        
        nav_layout = QVBoxLayout()
        nav_layout.setSpacing(6)
        nav_layout.addWidget(QLabel("<h3>Menu</h3>"))
        
        # Navigation buttons
        self.btn_dashboard = QPushButton("Dashboard")
        self.btn_books = QPushButton("Books")
        self.btn_students = QPushButton("Students")
        self.btn_issue = QPushButton("Issue Book")
        self.btn_return = QPushButton("Return Book")
        self.btn_reports = QPushButton("Reports")
        self.btn_export = QPushButton("Export CSV")
        self.btn_logout = QPushButton("Logout")
        self.btn_sync_drive = QPushButton("Sync to Drive")
        self.btn_google_logout = QPushButton("Logout Google")

        for b in [self.btn_dashboard, self.btn_books, self.btn_students,
                self.btn_issue, self.btn_return, self.btn_reports,
                self.btn_export, self.btn_sync_drive, self.btn_google_logout, 
                self.btn_logout,]:
            b.setMinimumWidth(160)
            nav_layout.addWidget(b)

        self.btn_sync_drive.clicked.connect(self.sync_to_drive)
        self.btn_google_logout.clicked.connect(self.logout_google)
        
        nav_layout.addStretch()
        
        self.stack = QStackedWidget()
        self.page_dashboard = self.create_dashboard_page()
        self.page_books = self.create_books_page()
        self.page_students = self.create_students_page()
        self.page_issue = self.create_issue_page()
        self.page_return = self.create_return_page()
        self.page_reports = self.create_reports_page()

        for p in [self.page_dashboard, self.page_books, self.page_students,
                  self.page_issue, self.page_return, self.page_reports]:
            self.stack.addWidget(p)

        main_layout.addLayout(nav_layout, 1)
        main_layout.addWidget(self.stack, 4)
        
        # Connect navigation buttons
        self.btn_dashboard.clicked.connect(lambda: self.switch_page(0))
        self.btn_books.clicked.connect(lambda: self.switch_page(1))
        self.btn_students.clicked.connect(lambda: self.switch_page(2))
        self.btn_issue.clicked.connect(lambda: self.switch_page(3))
        self.btn_return.clicked.connect(lambda: self.switch_page(4))
        self.btn_reports.clicked.connect(lambda: self.switch_page(5))
        self.btn_export.clicked.connect(self.export_all_csv)
        self.btn_logout.clicked.connect(self.logout)
        
        self.switch_page(0)
        self.overdue_timer = QTimer()
        self.overdue_timer.timeout.connect(self.check_overdue)
        self.overdue_timer.start(60 * 1000)  # 60 sec
        self.check_overdue()

    def prompt_barcode_scan(self):
        """Handle barcode scanning in different contexts based on current page"""
        current_page = self.stack.currentIndex()
        
        if current_page == 1: 
            self.scan_barcode_for_book_management()
        elif current_page == 3:  
            self.scan_barcode_for_issue()
        elif current_page == 4:  
            self.scan_barcode_for_return()
        else:
            self.scan_barcode_general()

    def scan_barcode_for_book_management(self):
        """Scan barcode in books management context"""
        barcode, ok = QInputDialog.getText(self, "Scan Book Barcode", 
                                          "Scan or enter book barcode:")
        if ok and barcode.strip():
            book = self.dbm.get_book_by_barcode(barcode.strip())
            if book:
                reply = QMessageBox.question(
                    self, 
                    "Book Found", 
                    f"Book found:\nTitle: {book['title']}\nAuthor: {book['author']}\n\nWhat would you like to do?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
                    QMessageBox.StandardButton.Yes
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    dlg = AddEditBookDialog(self.dbm, book=book, parent=self)
                    if dlg.exec():
                        self.refresh_books_table()
                elif reply == QMessageBox.StandardButton.No:
                    self.select_book_in_table(book['book_id'])
            else:
                reply = QMessageBox.question(
                    self,
                    "Book Not Found",
                    f"No book found with barcode: {barcode}\n\nWould you like to add a new book with this barcode?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.Yes:
                    dlg = AddEditBookDialog(self.dbm, barcode=barcode.strip(), parent=self)
                    if dlg.exec():
                        self.refresh_books_table()

    def scan_barcode_for_issue(self):
        """Scan barcode for book issuing"""
        barcode, ok = QInputDialog.getText(self, "Scan Book for Issue", 
                                          "Scan book barcode to issue:")
        if ok and barcode.strip():
            book = self.dbm.get_book_by_barcode(barcode.strip())
            if book:
                if book['quantity'] > 0:
                    for i in range(self.issue_book_combo.count()):
                        if self.issue_book_combo.itemData(i) == book['book_id']:
                            self.issue_book_combo.setCurrentIndex(i)
                            QMessageBox.information(
                                self, 
                                "Book Selected", 
                                f"Book '{book['title']}' selected for issuing.\nPlease select a student and complete the issue."
                            )
                            break
                else:
                    QMessageBox.warning(self, "No Copies Available", 
                                      "No copies of this book are available for issuing.")
            else:
                QMessageBox.warning(self, "Book Not Found", 
                                  f"No book found with barcode: {barcode}")

    def scan_barcode_for_return(self):
        """Scan barcode for book return"""
        barcode, ok = QInputDialog.getText(self, "Scan Book for Return", 
                                          "Scan book barcode to return:")
        if ok and barcode.strip():
            book = self.dbm.get_book_by_barcode(barcode.strip())
            if book:
                c = self.dbm.conn.cursor()
                c.execute("""
                    SELECT ib.issue_id, ib.book_id, b.title, ib.student_id, s.name as student_name,
                           ib.issue_date, ib.expected_return_date, ib.status
                    FROM issued_books ib
                    LEFT JOIN books b ON ib.book_id=b.book_id
                    LEFT JOIN students s ON ib.student_id=s.student_id
                    WHERE b.book_id=? AND ib.status='Issued'
                """, (book['book_id'],))
                
                issued_records = c.fetchall()
                
                if issued_records:
                    if len(issued_records) == 1:
                        issue_id = issued_records[0]['issue_id']
                        self.select_issue_in_return_table(issue_id)
                        QMessageBox.information(
                            self,
                            "Issue Record Found",
                            f"Book '{book['title']}' issued to {issued_records[0]['student_name']}.\nRecord selected for return."
                        )
                    else:
                        issues_list = "\n".join([f"ID: {r['issue_id']} - Student: {r['student_name']} - Issued: {r['issue_date']}" 
                                               for r in issued_records])
                        QMessageBox.information(
                            self,
                            "Multiple Issues Found",
                            f"Multiple issue records found for this book:\n\n{issues_list}\n\nPlease select the correct record from the table."
                        )
                        self.return_search.setText(book['title'])
                        self.refresh_return_page()
                else:
                    QMessageBox.information(self, "No Active Issues", 
                                          "This book is not currently issued to any student.")
            else:
                QMessageBox.warning(self, "Book Not Found", 
                                  f"No book found with barcode: {barcode}")

    def scan_barcode_general(self):
        """General barcode scanning for other pages"""
        barcode, ok = QInputDialog.getText(self, "Scan Book Barcode", 
                                          "Scan or enter book barcode:")
        if ok and barcode.strip():
            book = self.dbm.get_book_by_barcode(barcode.strip())
            if book:
                QMessageBox.information(
                    self,
                    "Book Information",
                    f"Title: {book['title']}\n"
                    f"Author: {book['author']}\n"
                    f"Category: {book['category']}\n"
                    f"Available Copies: {book['quantity']}\n"
                    f"Barcode: {book['barcode']}"
                )
            else:
                QMessageBox.warning(self, "Book Not Found", 
                                  f"No book found with barcode: {barcode}")

    def select_book_in_table(self, book_id):
        """Select a book in the books table"""
        for row in range(self.books_table.rowCount()):
            if self.books_table.item(row, 0).text() == str(book_id):
                self.books_table.selectRow(row)
                self.books_table.scrollToItem(self.books_table.item(row, 0))
                break

    def select_issue_in_return_table(self, issue_id):
        """Select an issue in the return table"""
        for row in range(self.return_table.rowCount()):
            if self.return_table.item(row, 0).text() == str(issue_id):
                self.return_table.selectRow(row)
                self.return_table.scrollToItem(self.return_table.item(row, 0))
                break

    def logout_google(self):
        confirm = QMessageBox.question(self, "Confirm Logout", "Logout from Google account?")
        if confirm != QMessageBox.StandardButton.Yes:
            return
        if google_logout():
            QMessageBox.information(self, "Logged Out", "Google account logged out successfully.")
        else:
            QMessageBox.warning(self, "Already Logged Out", "No Google account was logged in.")

    def switch_page(self, index):
        self.stack.setCurrentIndex(index)
        if index == 0:
            self.refresh_dashboard()
        elif index == 1:
            self.refresh_books_table()
        elif index == 2:
            self.refresh_students_table()
        elif index == 3:
            self.refresh_issue_page()
        elif index == 4:
            self.refresh_return_page()
        elif index == 5:
            self.refresh_reports_page()

    def logout(self):
        confirm = QMessageBox.question(self, "Logout", "Logout and return to login screen?")
        if confirm == QMessageBox.StandardButton.Yes:
            self.login = LoginWindow(self.dbm)
            self.login.show()
            self.close()

    # -------------------------
    # Dashboard
    # -------------------------
    def create_dashboard_page(self):
        w = QWidget()
        layout = QVBoxLayout()
        w.setLayout(layout)
        h = QLabel("<h2>Dashboard</h2>")
        layout.addWidget(h)

        self.lbl_total_books = QLabel()
        self.lbl_total_students = QLabel()
        self.lbl_issued_books = QLabel()
        self.lbl_overdue_list = QLabel("<b>Overdue:</b><br/><i>None</i>")

        layout.addWidget(self.lbl_total_books)
        layout.addWidget(self.lbl_total_students)
        layout.addWidget(self.lbl_issued_books)
        layout.addWidget(self.lbl_overdue_list)
        layout.addStretch()
        return w

    def refresh_dashboard(self):
        books = self.dbm.list_books()
        students = self.dbm.list_students()
        issued = self.dbm.list_issued()
        self.lbl_total_books.setText(f"<b>Total distinct book titles:</b> {len(books)}")
        total_copies = sum([row["quantity"] for row in books])
        self.lbl_total_books.setText(self.lbl_total_books.text() + f"  |  <b>Total copies available:</b> {total_copies}")
        self.lbl_total_students.setText(f"<b>Total students:</b> {len(students)}")
        self.lbl_issued_books.setText(f"<b>Currently issued books:</b> {len(issued)}")

        overdue = self.dbm.get_overdue()
        if overdue:
            html = "<b>Overdue:</b><ul>"
            for (issue_id, book_id, title, student_id, student_name, issue_date, expected_return_date, overdue_days) in overdue:
                html += f"<li>{title} — {student_name} — overdue by {overdue_days} day(s)</li>"
            html += "</ul>"
            self.lbl_overdue_list.setText(html)
        else:
            self.lbl_overdue_list.setText("<b>Overdue:</b><br/><i>None</i>")

    def check_overdue(self):
        overdue = self.dbm.get_overdue()
        if overdue:
            msgs = []
            for item in overdue[:5]:
                msgs.append(f"{item[2]} — {item[4]} (overdue by {item[7]} days)")
            txt = "\n".join(msgs)
            QMessageBox.information(self, "Overdue Notice", f"Overdue books detected:\n{txt}")
        self.refresh_dashboard()

    # -------------------------
    # Books Page
    # -------------------------
    def create_books_page(self):
        w = QWidget()
        layout = QVBoxLayout()
        w.setLayout(layout)
        header = QLabel("<h2>Books</h2>")
        layout.addWidget(header)
        action_layout = QHBoxLayout()
        self.book_search = QLineEdit()
        self.book_search.setPlaceholderText("Search by title, author, category, or barcode")
        self.book_search.returnPressed.connect(self.refresh_books_table)
        self.book_search_btn = QPushButton("Search")
        self.book_search_btn.clicked.connect(self.refresh_books_table)
        self.add_book_btn = QPushButton("Add Book")
        self.edit_book_btn = QPushButton("Edit Selected")
        self.delete_book_btn = QPushButton("Delete Selected")
        self.assign_barcode_btn = QPushButton("Assign Barcode")
        action_layout.addWidget(self.book_search)
        action_layout.addWidget(self.book_search_btn)
        action_layout.addWidget(self.add_book_btn)
        action_layout.addWidget(self.edit_book_btn)
        action_layout.addWidget(self.delete_book_btn)
        action_layout.addWidget(self.assign_barcode_btn)
        layout.addLayout(action_layout)
        self.books_table = QTableWidget(0, 6)
        self.books_table.setHorizontalHeaderLabels(["ID", "Title", "Author", "Category", "Quantity", "Barcode"])
        self.books_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.books_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.books_table)
        self.add_book_btn.clicked.connect(self.add_book)
        self.edit_book_btn.clicked.connect(self.edit_selected_book)
        self.delete_book_btn.clicked.connect(self.delete_selected_book)
        self.assign_barcode_btn.clicked.connect(self.assign_barcode_to_book)
        return w

    def refresh_books_table(self):
        q = self.book_search.text().strip()
        rows = self.dbm.list_books(q if q else None)
        self.books_table.setRowCount(0)
        for r in rows:
            row_idx = self.books_table.rowCount()
            self.books_table.insertRow(row_idx)
            self.books_table.setItem(row_idx, 0, QTableWidgetItem(str(r["book_id"])))
            self.books_table.setItem(row_idx, 1, QTableWidgetItem(r["title"]))
            self.books_table.setItem(row_idx, 2, QTableWidgetItem(r["author"] or ""))
            self.books_table.setItem(row_idx, 3, QTableWidgetItem(r["category"] or ""))
            self.books_table.setItem(row_idx, 4, QTableWidgetItem(str(r["quantity"])))
            self.books_table.setItem(row_idx, 5, QTableWidgetItem(r["barcode"] or ""))

    def get_selected_book_id(self):
        sel = self.books_table.selectedItems()
        if not sel:
            return None
        book_id = int(sel[0].text())
        return book_id

    def add_book(self):
        dlg = AddEditBookDialog(self.dbm, parent=self)
        if dlg.exec():
            self.refresh_books_table()

    def edit_selected_book(self):
        bid = self.get_selected_book_id()
        if not bid:
            QMessageBox.warning(self, "No selection", "Please select a book to edit.")
            return
        book = self.dbm.get_book(bid)
        dlg = AddEditBookDialog(self.dbm, book=book, parent=self)
        if dlg.exec():
            self.refresh_books_table()

    def delete_selected_book(self):
        bid = self.get_selected_book_id()
        if not bid:
            QMessageBox.warning(self, "No selection", "Please select a book to delete.")
            return
        confirm = QMessageBox.question(self, "Confirm Delete", "Delete selected book?")
        if confirm != QMessageBox.StandardButton.Yes:
            return
        try:
            self.dbm.delete_book(bid)
            QMessageBox.information(self, "Deleted", "Book deleted.")
            self.refresh_books_table()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def assign_barcode_to_book(self):
        """Assign or update barcode for selected book"""
        bid = self.get_selected_book_id()
        if not bid:
            QMessageBox.warning(self, "No selection", "Please select a book to assign barcode.")
            return
            
        barcode, ok = QInputDialog.getText(self, "Assign Barcode", 
                                          "Scan or enter barcode for selected book:")
        if ok and barcode.strip():
            try:
                self.dbm.update_book_barcode(bid, barcode.strip())
                QMessageBox.information(self, "Barcode Assigned", "Barcode assigned successfully.")
                self.refresh_books_table()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to assign barcode: {str(e)}")

    # -------------------------
    # Students Page
    # -------------------------
    def create_students_page(self):
        w = QWidget()
        layout = QVBoxLayout()
        w.setLayout(layout)
        layout.addWidget(QLabel("<h2>Students</h2>"))

        action_layout = QHBoxLayout()
        self.student_search = QLineEdit()
        self.student_search.setPlaceholderText("Search by name, class or contact")
        self.student_search.returnPressed.connect(self.refresh_students_table)
        self.student_search_btn = QPushButton("Search")
        self.student_search_btn.clicked.connect(self.refresh_students_table)
        self.add_student_btn = QPushButton("Add Student")
        self.edit_student_btn = QPushButton("Edit Selected")
        self.delete_student_btn = QPushButton("Delete Selected")

        action_layout.addWidget(self.student_search)
        action_layout.addWidget(self.student_search_btn)
        action_layout.addWidget(self.add_student_btn)
        action_layout.addWidget(self.edit_student_btn)
        action_layout.addWidget(self.delete_student_btn)
        layout.addLayout(action_layout)

        self.students_table = QTableWidget(0, 4)
        self.students_table.setHorizontalHeaderLabels(["ID", "Name", "Class", "Contact"])
        self.students_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.students_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.students_table)

        self.add_student_btn.clicked.connect(self.add_student)
        self.edit_student_btn.clicked.connect(self.edit_selected_student)
        self.delete_student_btn.clicked.connect(self.delete_selected_student)

        return w

    def refresh_students_table(self):
        q = self.student_search.text().strip()
        rows = self.dbm.list_students(q if q else None)
        self.students_table.setRowCount(0)
        for r in rows:
            row_idx = self.students_table.rowCount()
            self.students_table.insertRow(row_idx)
            self.students_table.setItem(row_idx, 0, QTableWidgetItem(str(r["student_id"])))
            self.students_table.setItem(row_idx, 1, QTableWidgetItem(r["name"]))
            self.students_table.setItem(row_idx, 2, QTableWidgetItem(r["class"] or ""))
            self.students_table.setItem(row_idx, 3, QTableWidgetItem(r["contact"] or ""))

    def get_selected_student_id(self):
        sel = self.students_table.selectedItems()
        if not sel:
            return None
        student_id = int(sel[0].text())
        return student_id

    def add_student(self):
        dlg = AddEditStudentDialog(self.dbm, parent=self)
        if dlg.exec():
            self.refresh_students_table()

    def edit_selected_student(self):
        sid = self.get_selected_student_id()
        if not sid:
            QMessageBox.warning(self, "No selection", "Please select a student to edit.")
            return
        student = self.dbm.get_student(sid)
        dlg = AddEditStudentDialog(self.dbm, student=student, parent=self)
        if dlg.exec():
            self.refresh_students_table()

    def delete_selected_student(self):
        sid = self.get_selected_student_id()
        if not sid:
            QMessageBox.warning(self, "No selection", "Please select a student to delete.")
            return
        confirm = QMessageBox.question(self, "Confirm Delete", "Delete selected student?")
        if confirm != QMessageBox.StandardButton.Yes:
            return
        try:
            self.dbm.delete_student(sid)
            QMessageBox.information(self, "Deleted", "Student deleted.")
            self.refresh_students_table()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    # -------------------------
    # Issue Page
    # -------------------------
    def create_issue_page(self):
        w = QWidget()
        layout = QVBoxLayout()
        w.setLayout(layout)
        layout.addWidget(QLabel("<h2>Issue Book</h2>"))

        form_group = QGroupBox("Issue details")
        form_layout = QFormLayout()

        self.issue_student_combo = QComboBox()
        self.issue_book_combo = QComboBox()
        self.issue_issue_date = QDateEdit()
        self.issue_issue_date.setCalendarPopup(True)
        self.issue_issue_date.setDate(QDate.currentDate())
        self.issue_return_date = QDateEdit()
        self.issue_return_date.setCalendarPopup(True)
        self.issue_return_date.setDate(QDate.currentDate().addDays(7))

        form_layout.addRow("Student:", self.issue_student_combo)
        form_layout.addRow("Book:", self.issue_book_combo)
        form_layout.addRow("Issue Date:", self.issue_issue_date)
        form_layout.addRow("Expected Return:", self.issue_return_date)

        form_group.setLayout(form_layout)
        layout.addWidget(form_group)

        btn_layout = QHBoxLayout()
        self.issue_btn = QPushButton("Issue Book")
        self.issue_refresh_btn = QPushButton("Refresh lists")
        self.issue_scan_btn = QPushButton("Scan Book Barcode")
        btn_layout.addWidget(self.issue_btn)
        btn_layout.addWidget(self.issue_refresh_btn)
        btn_layout.addWidget(self.issue_scan_btn)
        layout.addLayout(btn_layout)

        layout.addWidget(QLabel("<b>Currently Issued Books</b>"))
        self.issued_table = QTableWidget(0, 6)
        self.issued_table.setHorizontalHeaderLabels(["Issue ID", "Book", "Student", "Issue Date", "Expected Return", "Status"])
        self.issued_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.issued_table)

        self.issue_btn.clicked.connect(self.issue_book)
        self.issue_refresh_btn.clicked.connect(self.refresh_issue_page)
        self.issue_scan_btn.clicked.connect(self.scan_barcode_for_issue)

        return w

    def refresh_issue_page(self):
        self.issue_student_combo.clear()
        students = self.dbm.list_students()
        for s in students:
            self.issue_student_combo.addItem(f"{s['name']} ({s['class']})", s["student_id"])
        self.issue_book_combo.clear()
        books = self.dbm.list_books()
        for b in books:
            if int(b["quantity"]) > 0:
                self.issue_book_combo.addItem(f"{b['title']} by {b['author'] or 'Unknown'}  [{b['quantity']} copies]", b["book_id"])
        rows = self.dbm.list_issued()
        self.issued_table.setRowCount(0)
        for r in rows:
            idx = self.issued_table.rowCount()
            self.issued_table.insertRow(idx)
            self.issued_table.setItem(idx, 0, QTableWidgetItem(str(r["issue_id"])))
            self.issued_table.setItem(idx, 1, QTableWidgetItem(r["title"]))
            self.issued_table.setItem(idx, 2, QTableWidgetItem(r["student_name"]))
            self.issued_table.setItem(idx, 3, QTableWidgetItem(r["issue_date"]))
            self.issued_table.setItem(idx, 4, QTableWidgetItem(r["expected_return_date"]))
            self.issued_table.setItem(idx, 5, QTableWidgetItem(r["status"]))

    def issue_book(self):
        sid_idx = self.issue_student_combo.currentIndex()
        bid_idx = self.issue_book_combo.currentIndex()
        if sid_idx < 0 or bid_idx < 0:
            QMessageBox.warning(self, "Selection missing", "Choose a student and a book.")
            return
        student_id = self.issue_student_combo.currentData()
        book_id = self.issue_book_combo.currentData()
        issue_date = self.issue_issue_date.date().toPyDate()
        expected = self.issue_return_date.date().toPyDate()
        if expected < issue_date:
            QMessageBox.warning(self, "Invalid date", "Expected return date cannot be before issue date.")
            return
        try:
            self.dbm.issue_book(book_id, student_id, issue_date.strftime("%Y-%m-%d"), expected.strftime("%Y-%m-%d"))
            QMessageBox.information(self, "Issued", "Book issued successfully.")
            self.refresh_issue_page()
            self.refresh_books_table()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    # -------------------------
    # Return Page
    # -------------------------
    def create_return_page(self):
        w = QWidget()
        layout = QVBoxLayout()
        w.setLayout(layout)
        layout.addWidget(QLabel("<h2>Return Book</h2>"))

        action_layout = QHBoxLayout()
        self.return_search = QLineEdit()
        self.return_search.setPlaceholderText("Search issued by book title, student name, or barcode")
        self.return_search.returnPressed.connect(self.refresh_return_page)
        self.return_search_btn = QPushButton("Search")
        self.return_search_btn.clicked.connect(self.refresh_return_page)
        self.return_btn = QPushButton("Mark as Returned")
        self.return_scan_btn = QPushButton("Scan Book Barcode")

        action_layout.addWidget(self.return_search)
        action_layout.addWidget(self.return_search_btn)
        action_layout.addWidget(self.return_btn)
        action_layout.addWidget(self.return_scan_btn)
        layout.addLayout(action_layout)

        self.return_table = QTableWidget(0, 7)
        self.return_table.setHorizontalHeaderLabels(["Issue ID", "Book", "Student", "Issue Date", "Expected Return", "Status", "Overdue Days"])
        self.return_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.return_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.return_table)

        self.return_btn.clicked.connect(self.mark_returned)
        self.return_scan_btn.clicked.connect(self.scan_barcode_for_return)

        return w

    def refresh_return_page(self):
        q = self.return_search.text().strip()
        rows = self.dbm.list_issued(search=q if q else None)
        self.return_table.setRowCount(0)
        for r in rows:
            idx = self.return_table.rowCount()
            self.return_table.insertRow(idx)
            self.return_table.setItem(idx, 0, QTableWidgetItem(str(r["issue_id"])))
            self.return_table.setItem(idx, 1, QTableWidgetItem(r["title"]))
            self.return_table.setItem(idx, 2, QTableWidgetItem(r["student_name"]))
            self.return_table.setItem(idx, 3, QTableWidgetItem(r["issue_date"]))
            self.return_table.setItem(idx, 4, QTableWidgetItem(r["expected_return_date"]))
            self.return_table.setItem(idx, 5, QTableWidgetItem(r["status"]))
            expected = datetime.strptime(r["expected_return_date"], "%Y-%m-%d").date()
            overdue_days = (date.today() - expected).days
            self.return_table.setItem(idx, 6, QTableWidgetItem(str(overdue_days if overdue_days > 0 else 0)))

    def get_selected_issue_id(self):
        sel = self.return_table.selectedItems()
        if not sel:
            return None
        return int(sel[0].text())

    def mark_returned(self):
        issue_id = self.get_selected_issue_id()
        if not issue_id:
            QMessageBox.warning(self, "No selection", "Select an issued record to return.")
            return
        confirm = QMessageBox.question(self, "Confirm Return", "Mark selected book as returned?")
        if confirm != QMessageBox.StandardButton.Yes:
            return
        try:
            actual = date.today().strftime("%Y-%m-%d")
            self.dbm.return_book(issue_id, actual)
            QMessageBox.information(self, "Returned", "Book marked as returned.")
            self.refresh_return_page()
            self.refresh_books_table()
            self.refresh_dashboard()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    # -------------------------
    # Reports Page
    # -------------------------
    def create_reports_page(self):
        w = QWidget()
        layout = QVBoxLayout()
        w.setLayout(layout)
        layout.addWidget(QLabel("<h2>Reports</h2>"))

        btn_layout = QHBoxLayout()
        self.btn_list_all_issues = QPushButton("All Issues")
        self.btn_list_overdue = QPushButton("Overdue")
        self.btn_top_books = QPushButton("Top Books (by past issues)")
        btn_layout.addWidget(self.btn_list_all_issues)
        btn_layout.addWidget(self.btn_list_overdue)
        btn_layout.addWidget(self.btn_top_books)
        layout.addLayout(btn_layout)

        self.report_table = QTableWidget(0, 8)
        self.report_table.setHorizontalHeaderLabels(["Issue ID", "Book", "Student", "Issue Date", "Expected Return", "Returned On", "Status", "Overdue Days"])
        self.report_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.report_table)

        self.btn_list_all_issues.clicked.connect(self.report_all_issues)
        self.btn_list_overdue.clicked.connect(self.report_overdue)
        self.btn_top_books.clicked.connect(self.report_top_books)

        return w

    def refresh_reports_page(self):
        self.report_all_issues()

    def report_all_issues(self):
        rows = self.dbm.list_all_issues()
        self.report_table.setRowCount(0)
        for r in rows:
            idx = self.report_table.rowCount()
            self.report_table.insertRow(idx)
            self.report_table.setItem(idx, 0, QTableWidgetItem(str(r["issue_id"])))
            self.report_table.setItem(idx, 1, QTableWidgetItem(r["title"]))
            self.report_table.setItem(idx, 2, QTableWidgetItem(r["student_name"]))
            self.report_table.setItem(idx, 3, QTableWidgetItem(r["issue_date"]))
            self.report_table.setItem(idx, 4, QTableWidgetItem(r["expected_return_date"]))
            self.report_table.setItem(idx, 5, QTableWidgetItem(r["actual_return_date"] or ""))
            self.report_table.setItem(idx, 6, QTableWidgetItem(r["status"]))
            overdue = 0
            if r["status"] == "Issued":
                expected = datetime.strptime(r["expected_return_date"], "%Y-%m-%d").date()
                overdue = (date.today() - expected).days
                overdue = overdue if overdue > 0 else 0
            self.report_table.setItem(idx, 7, QTableWidgetItem(str(overdue)))

    def report_overdue(self):
        overdue = self.dbm.get_overdue()
        self.report_table.setRowCount(0)
        for item in overdue:
            (issue_id, book_id, title, student_id, student_name, issue_date, expected_return_date, overdue_days) = item
            idx = self.report_table.rowCount()
            self.report_table.insertRow(idx)
            self.report_table.setItem(idx, 0, QTableWidgetItem(str(issue_id)))
            self.report_table.setItem(idx, 1, QTableWidgetItem(title))
            self.report_table.setItem(idx, 2, QTableWidgetItem(student_name))
            self.report_table.setItem(idx, 3, QTableWidgetItem(issue_date))
            self.report_table.setItem(idx, 4, QTableWidgetItem(expected_return_date))
            self.report_table.setItem(idx, 5, QTableWidgetItem(""))
            self.report_table.setItem(idx, 6, QTableWidgetItem("Issued"))
            self.report_table.setItem(idx, 7, QTableWidgetItem(str(overdue_days)))

    def report_top_books(self):
        c = self.dbm.conn.cursor()
        c.execute("""
            SELECT b.book_id, b.title, b.author, COUNT(ib.issue_id) AS times_issued
            FROM books b
            LEFT JOIN issued_books ib ON b.book_id = ib.book_id
            GROUP BY b.book_id
            ORDER BY times_issued DESC, b.title
            LIMIT 20
        """)
        rows = c.fetchall()
        self.report_table.setRowCount(0)
        for r in rows:
            idx = self.report_table.rowCount()
            self.report_table.insertRow(idx)
            self.report_table.setItem(idx, 0, QTableWidgetItem(str(r["book_id"])))
            self.report_table.setItem(idx, 1, QTableWidgetItem(r["title"]))
            self.report_table.setItem(idx, 2, QTableWidgetItem(r["author"] or ""))
            self.report_table.setItem(idx, 3, QTableWidgetItem(str(r["times_issued"])))
            for col in range(4, 8):
                self.report_table.setItem(idx, col, QTableWidgetItem(""))

    # -------------------------
    # Sync in Drive for Backup
    # -------------------------
    def on_sync_success(self, message):
        QMessageBox.information(self, "Sync Complete", message)

    def on_sync_error(self, error):
        QMessageBox.critical(self, "Sync Failed", f"Error: {error}")

    def on_sync_finished(self):
        if hasattr(self, "wait_dialog") and self.wait_dialog.isVisible():
            self.wait_dialog.accept() 
        self.refresh_dashboard()

    def sync_to_drive(self):
        if not os.path.exists("token.pickle"):
            choice = QMessageBox.question(
                self,
                "Google Login Required",
                "You are not logged in to Google. Do you want to log in now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if choice == QMessageBox.StandardButton.No:
                return
            try:
                google_login()
                QMessageBox.information(self, "Login Success", "Logged in successfully! You can now sync.")
            except Exception as e:
                QMessageBox.critical(self, "Login Failed", f"Error logging in: {e}")
                return
        self.wait_dialog = QDialog(self)
        self.wait_dialog.setWindowTitle("Syncing")
        self.wait_dialog.setModal(True)
        self.wait_dialog.resize(300, 120)
        layout = QVBoxLayout()
        label = QLabel("Please wait... Syncing your data to Google Drive.")
        layout.addWidget(label)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        layout.addWidget(self.progress)
        self.wait_dialog.setLayout(layout)
        self.wait_dialog.show()

        self.threadpool = getattr(self, "threadpool", QThreadPool())
        worker = DriveSyncWorker(self.dbm)
        worker.signals.success.connect(self.on_sync_success)
        worker.signals.error.connect(self.on_sync_error)
        worker.signals.finished.connect(self.on_sync_finished)
        self.threadpool.start(worker)

    # -------------------------
    # Export CSV
    # -------------------------
    def export_all_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Books CSV", "books_export.csv", "CSV Files (*.csv)")
        if not path:
            return
        try:
            self.dbm.export_table_csv("books", path)
            QMessageBox.information(self, "Exported", f"Books exported to {path}")
        except Exception as e:
            QMessageBox.critical(self, "Export error", str(e))

    def closeEvent(self, event):
        if not QApplication.instance().closingDown():
            event.accept()
            return
        self.dbm.close()
        event.accept()

