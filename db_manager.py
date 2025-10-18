import sqlite3
import csv
from datetime import date, datetime

DB_FILE = "library.db"


class DatabaseManager:
    def __init__(self, db_path=DB_FILE):
        self.db_path = db_path
        self.conn = sqlite3.connect("library.db", check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        c = self.conn.cursor()

        c.execute("""
        CREATE TABLE IF NOT EXISTS books (
            book_id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT,
            category TEXT,
            quantity INTEGER DEFAULT 1,
            barcode TEXT UNIQUE
        )
        """)
        c.execute("""
        CREATE TABLE IF NOT EXISTS students (
            student_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            class TEXT,
            contact TEXT
        )
        """)
        c.execute("""
        CREATE TABLE IF NOT EXISTS issued_books (
            issue_id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER,
            student_id INTEGER,
            issue_date TEXT,
            expected_return_date TEXT,
            actual_return_date TEXT,
            status TEXT,
            FOREIGN KEY(book_id) REFERENCES books(book_id),
            FOREIGN KEY(student_id) REFERENCES students(student_id)
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT
        )
        """)
        c.execute("PRAGMA table_info(books)")
        existing_cols = [row[1] for row in c.fetchall()]
        if "barcode" not in existing_cols:
            c.execute("ALTER TABLE books ADD COLUMN barcode TEXT UNIQUE")
            self.conn.commit()
        if "added_date" not in existing_cols:
            c.execute("ALTER TABLE books ADD COLUMN added_date TEXT")
            self.conn.commit()
        c.execute("""
            CREATE TABLE IF NOT EXISTS students (
                student_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                class TEXT,
                contact TEXT
            )
            """)
        c.execute("SELECT COUNT(*) FROM users")
        if c.fetchone()[0] == 0:
            c.execute("INSERT INTO users (username, password) VALUES (?,?)", ("admin", "admin"))
        self.conn.commit()

        c.execute("SELECT COUNT(*) FROM books")
        if c.fetchone()[0] == 0:
            sample_books = [
                ("Mathematics - Class 10", "R.S. Aggarwal", "Textbook", 5),
                ("Science - Class 9", "Lakhmir Singh", "Textbook", 4),
                ("Python Programming", "John Zelle", "Programming", 2),
                ("Harry Potter and the Sorcerer's Stone", "J.K. Rowling", "Fiction", 3),
            ]
            c.executemany("INSERT INTO books (title,author,category,quantity) VALUES (?,?,?,?)", sample_books)
            self.conn.commit()

        c.execute("SELECT COUNT(*) FROM students")
        if c.fetchone()[0] == 0:
            sample_students = [
                ("Aman Sharma", "10-A", "9876543210"),
                ("Riya Kapoor", "9-B", "9876501234"),
                ("Rahul Verma", "11-C", "9123456789")
            ]
            c.executemany("INSERT INTO students (name,class,contact) VALUES (?,?,?)", sample_students)
            self.conn.commit()


    def validate_user(self, username, password):
        c = self.conn.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        return c.fetchone() is not None


    def add_book(self, title, author, category, quantity):
        c = self.conn.cursor()
        added_date = date.today().strftime("%Y-%m-%d")
        c.execute("INSERT INTO books (title, author, category, quantity, added_date) VALUES (?, ?, ?, ?, ?)",
              (title, author, category, quantity, added_date))
        self.conn.commit()
        return c.lastrowid


    def update_book(self, book_id, title, author, category, quantity):
        c = self.conn.cursor()
        c.execute("UPDATE books SET title=?, author=?, category=?, quantity=? WHERE book_id=?",
                  (title, author, category, quantity, book_id))
        self.conn.commit()

    def delete_book(self, book_id):
        c = self.conn.cursor()
        c.execute("SELECT COUNT(*) FROM issued_books WHERE book_id=? AND status='Issued'", (book_id,))
        if c.fetchone()[0] > 0:
            raise Exception("Cannot delete: book currently issued to a student.")
        c.execute("DELETE FROM books WHERE book_id=?", (book_id,))
        self.conn.commit()

    def list_books(self, search=None):
        c = self.conn.cursor()
        if search:
            s = f"%{search}%"
            c.execute("SELECT * FROM books WHERE title LIKE ? OR author LIKE ? OR category LIKE ? ORDER BY title",
                      (s, s, s))
        else:
            c.execute("SELECT * FROM books ORDER BY title")
        return c.fetchall()

    def get_book(self, book_id):
        c = self.conn.cursor()
        c.execute("SELECT * FROM books WHERE book_id=?", (book_id,))
        return c.fetchone()


    def add_student(self, name, sclass, contact):
        c = self.conn.cursor()
        c.execute("INSERT INTO students (name,class,contact) VALUES (?,?,?)", (name, sclass, contact))
        self.conn.commit()
        return c.lastrowid

    def update_student(self, student_id, name, sclass, contact):
        c = self.conn.cursor()
        c.execute("UPDATE students SET name=?, class=?, contact=? WHERE student_id=?",
                  (name, sclass, contact, student_id))
        self.conn.commit()

    def delete_student(self, student_id):
        c = self.conn.cursor()
        c.execute("SELECT COUNT(*) FROM issued_books WHERE student_id=? AND status='Issued'", (student_id,))
        if c.fetchone()[0] > 0:
            raise Exception("Cannot delete: student has issued books.")
        c.execute("DELETE FROM students WHERE student_id=?", (student_id,))
        self.conn.commit()

    def list_students(self, search=None):
        c = self.conn.cursor()
        if search:
            s = f"%{search}%"
            c.execute("SELECT * FROM students WHERE name LIKE ? OR class LIKE ? OR contact LIKE ? ORDER BY name",
                      (s, s, s))
        else:
            c.execute("SELECT * FROM students ORDER BY name")
        return c.fetchall()

    def get_student(self, student_id):
        c = self.conn.cursor()
        c.execute("SELECT * FROM students WHERE student_id=?", (student_id,))
        return c.fetchone()

    def issue_book(self, book_id, student_id, issue_date, expected_return_date):
        c = self.conn.cursor()
        c.execute("SELECT quantity FROM books WHERE book_id=?", (book_id,))
        row = c.fetchone()
        if not row:
            raise Exception("Book not found.")
        if row["quantity"] <= 0:
            raise Exception("No copies available to issue.")
        c.execute("""INSERT INTO issued_books (book_id,student_id,issue_date,expected_return_date,status)
                     VALUES (?,?,?,?,?)""",
                  (book_id, student_id, issue_date, expected_return_date, "Issued"))
        c.execute("UPDATE books SET quantity = quantity - 1 WHERE book_id=?", (book_id,))
        self.conn.commit()
        return c.lastrowid

    def return_book(self, issue_id, actual_return_date):
        c = self.conn.cursor()
        c.execute("SELECT * FROM issued_books WHERE issue_id=?", (issue_id,))
        rec = c.fetchone()
        if not rec:
            raise Exception("Issue record not found.")
        if rec["status"] != "Issued":
            raise Exception("Book already returned.")
        c.execute("UPDATE issued_books SET actual_return_date=?, status=? WHERE issue_id=?",
                  (actual_return_date, "Returned", issue_id))
        c.execute("UPDATE books SET quantity = quantity + 1 WHERE book_id=?", (rec["book_id"],))
        self.conn.commit()

    def list_issued(self, only_issued=True, search=None):
        c = self.conn.cursor()
        base = """SELECT ib.issue_id, ib.book_id, b.title, b.author, ib.student_id, s.name as student_name,
                  ib.issue_date, ib.expected_return_date, ib.actual_return_date, ib.status
                  FROM issued_books ib
                  LEFT JOIN books b ON ib.book_id=b.book_id
                  LEFT JOIN students s ON ib.student_id=s.student_id"""
        conds = []
        params = []
        if only_issued:
            conds.append("ib.status='Issued'")
        if search:
            s = f"%{search}%"
            conds.append("(b.title LIKE ? OR s.name LIKE ?)")
            params += [s, s]
        if conds:
            base += " WHERE " + " AND ".join(conds)
        base += " ORDER BY ib.issue_date DESC"
        c.execute(base, params)
        return c.fetchall()

    def list_all_issues(self, search=None):
        return self.list_issued(only_issued=False, search=search)

    def get_issue(self, issue_id):
        c = self.conn.cursor()
        c.execute("SELECT * FROM issued_books WHERE issue_id=?", (issue_id,))
        return c.fetchone()


    def export_table_csv(self, table_name, csv_path):
        c = self.conn.cursor()
        c.execute(f"SELECT * FROM {table_name}")
        rows = c.fetchall()
        if not rows:
            raise Exception("No data to export.")
        columns = rows[0].keys()
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(columns)
            for r in rows:
                writer.writerow([r[col] for col in columns])
    def get_book_by_barcode(self, barcode):
        """Fetch a single book record by barcode."""
        c = self.conn.cursor()
        c.execute("SELECT * FROM books WHERE barcode=?", (barcode,))
        return c.fetchone()

    def update_book_barcode(self, book_id, barcode):
        """Update or assign a barcode to an existing book."""
        c = self.conn.cursor()
        c.execute("UPDATE books SET barcode=? WHERE book_id=?", (barcode, book_id))
        self.conn.commit()

    def add_book_with_barcode(self, title, author, category, quantity, barcode=None):
        """Add a book and optionally store its barcode."""
        c = self.conn.cursor()
        c.execute("INSERT INTO books (title, author, category, quantity, barcode) VALUES (?,?,?,?,?)",
                (title, author, category, quantity, barcode))
        self.conn.commit()
        return c.lastrowid


    def get_overdue(self, as_of_date=None):
        if as_of_date is None:
            as_of_date = date.today()
        c = self.conn.cursor()
        c.execute("""SELECT ib.issue_id, ib.book_id, b.title, ib.student_id, s.name,
                     ib.issue_date, ib.expected_return_date
                     FROM issued_books ib
                     LEFT JOIN books b ON ib.book_id=b.book_id
                     LEFT JOIN students s ON ib.student_id=s.student_id
                     WHERE ib.status='Issued'""")
        res = []
        for row in c.fetchall():
            expected = datetime.strptime(row["expected_return_date"], "%Y-%m-%d").date()
            overdue_days = (as_of_date - expected).days
            if overdue_days > 0:
                res.append((row["issue_id"], row["book_id"], row["title"], row["student_id"], row["name"],
                            row["issue_date"], row["expected_return_date"], overdue_days))
        return res
   
    def close(self):
        self.conn.close()
