from PyQt6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLineEdit, QInputDialog, QHBoxLayout, QPushButton, QMessageBox



# Dialog Classes
class AddEditBookDialog(QDialog):
    def __init__(self, dbm, book=None, barcode=None, parent=None):
        super().__init__(parent)
        self.dbm = dbm
        self.book = book
        self.setWindowTitle("Edit Book" if book else "Add New Book")
        self.resize(400, 300)
        
        layout = QVBoxLayout()
        form = QFormLayout()
        
        self.title_input = QLineEdit()
        self.author_input = QLineEdit()
        self.category_input = QLineEdit()
        self.quantity_input = QLineEdit()
        self.quantity_input.setText("1")
        self.barcode_input = QLineEdit()
        
        if book:
            self.title_input.setText(book['title'])
            self.author_input.setText(book['author'] or '')
            self.category_input.setText(book['category'] or '')
            self.quantity_input.setText(str(book['quantity']))
            self.barcode_input.setText(book['barcode'] or '')
        elif barcode:
            self.barcode_input.setText(barcode)
        
        form.addRow("Title *:", self.title_input)
        form.addRow("Author:", self.author_input)
        form.addRow("Category:", self.category_input)
        form.addRow("Quantity *:", self.quantity_input)
        form.addRow("Barcode:", self.barcode_input)
        
        layout.addLayout(form)
        
        # Scan barcode button
        scan_layout = QHBoxLayout()
        self.scan_btn = QPushButton("📠 Scan Barcode")
        self.scan_btn.clicked.connect(self.scan_barcode)
        scan_layout.addWidget(self.scan_btn)
        scan_layout.addStretch()
        layout.addLayout(scan_layout)
        
        # Buttons
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save")
        self.cancel_btn = QPushButton("Cancel")
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
        
        self.save_btn.clicked.connect(self.save_book)
        self.cancel_btn.clicked.connect(self.reject)
        
    def scan_barcode(self):
        barcode, ok = QInputDialog.getText(self, "Scan Barcode", "Scan or enter barcode:")
        if ok and barcode.strip():
            self.barcode_input.setText(barcode.strip())
            
    def save_book(self):
        title = self.title_input.text().strip()
        author = self.author_input.text().strip()
        category = self.category_input.text().strip()
        quantity = self.quantity_input.text().strip()
        barcode = self.barcode_input.text().strip() or None
        
        if not title:
            QMessageBox.warning(self, "Validation Error", "Title is required.")
            return
        if not quantity or not quantity.isdigit():
            QMessageBox.warning(self, "Validation Error", "Valid quantity is required.")
            return
            
        quantity = int(quantity)
        
        try:
            if self.book:
                self.dbm.update_book(self.book['book_id'], title, author, category, quantity)
                if barcode:
                    self.dbm.update_book_barcode(self.book['book_id'], barcode)
            else:
                if barcode:
                    existing = self.dbm.get_book_by_barcode(barcode)
                    if existing:
                        QMessageBox.warning(self, "Duplicate Barcode", 
                                          f"Barcode already assigned to: {existing['title']}")
                        return
                    self.dbm.add_book_with_barcode(title, author, category, quantity, barcode)
                else:
                    self.dbm.add_book(title, author, category, quantity)
                    
            QMessageBox.information(self, "Success", "Book saved successfully.")
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save book: {str(e)}")

class AddEditStudentDialog(QDialog):
    def __init__(self, dbm, student=None, parent=None):
        super().__init__(parent)
        self.dbm = dbm
        self.student = student
        self.setWindowTitle("Edit Student" if student else "Add New Student")
        self.resize(400, 200)
        
        layout = QVBoxLayout()
        form = QFormLayout()
        
        self.name_input = QLineEdit()
        self.class_input = QLineEdit()
        self.contact_input = QLineEdit()
        
        if student:
            self.name_input.setText(student['name'])
            self.class_input.setText(student['class'] or '')
            self.contact_input.setText(student['contact'] or '')
        
        form.addRow("Name *:", self.name_input)
        form.addRow("Class:", self.class_input)
        form.addRow("Contact:", self.contact_input)
        
        layout.addLayout(form)
        
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save")
        self.cancel_btn = QPushButton("Cancel")
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
        
        self.save_btn.clicked.connect(self.save_student)
        self.cancel_btn.clicked.connect(self.reject)
        
    def save_student(self):
        name = self.name_input.text().strip()
        sclass = self.class_input.text().strip()
        contact = self.contact_input.text().strip()
        
        if not name:
            QMessageBox.warning(self, "Validation Error", "Name is required.")
            return
            
        try:
            if self.student:
                self.dbm.update_student(self.student['student_id'], name, sclass, contact)
            else:
                self.dbm.add_student(name, sclass, contact)
                
            QMessageBox.information(self, "Success", "Student saved successfully.")
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save student: {str(e)}")
