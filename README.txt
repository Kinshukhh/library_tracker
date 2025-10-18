============================================================

Library Management System (Multiple-files)

============================================================

Overview

The Library Management System is a desktop application built using Python (PyQt6) and SQLite.
It is designed to manage books, students, and library transactions such as issuing and returning books.
The system includes a graphical interface, local data storage, cloud data storage and an optional executable file for fast access.

Project Information

Framework: PyQt6
Database: SQLite (library.db)
Executable: Included (Library_Tracker.exe) – created using PyInstaller
Command for Executable: pyinstaller --noconfirm --clean --onefile --windowed --icon=library.ico --add-data "library.db;." --add-data "library.ico;." --add-data "token.pickle;." --hidden-import "google.auth.transport.requests" --hidden-import "google_auth_oauthlib.flow" --hidden-import "gspread" --hidden-import "requests" main.py

Library_project/
│
├── main.py                # Entry point of the application
├── main_gui.py            # GUI layout and main window logic
├── db_manager.py          # Handles all database interactions (SQLite)
├── dialogs.py             # Add/Edit dialogs for books and students
├── library.db             # SQLite database file (auto-created if missing)
├── EXE                    # Folder for .exe
    └──  Library_Tracker.exe    # Pre-built executable for quick launch SIZE: (48.3 MB) RAM USAGE: (MAX 100 MB) BUILT ALL LATEST OS
└── library.ico            # Sora AI made Logo is used as .exe logo (https://sora.chatgpt.com/g/gen_01k7s395nbfh48j3xqk996ghmj)
└── README.txt              # Documentation file
└── Other Documentation              # Folder for .txt files
    └── sources.txt            # Sources for program used  
    └── summary.txt            # Summary of README
└── token.pickle # Mainly for building .exe usage in code for oauth of Google
============================================================

Requirements

============================================================

Python Version

Python 3.11 or higher is recommended.

===========================================================

[] Required Packages :

If running from source, install dependencies using:

pip install gspread google-auth-oauthlib google-auth requests PyQt6


SQLite3 comes with Python by default, so no separate installation is required.

============================================================

How to Run

============================================================

Option 1: Run Using Python Source Files

Install dependencies:

pip install gspread google-auth-oauthlib google-auth requests PyQt6


Run the main application:

python main.py

Option 2: Run Using the Executable

For faster startup, use the pre-built executable:

Library_Tracker.exe


No Python installation is required for this method.

Default Admin Login

============================================================

Username	Password
admin	admin
Database Information

============================================================

Database file: library.db
Database type: SQLite

Tables

books – Stores book details such as title, author, and quantity.

students – Stores student details such as name, class, and roll number.

transactions – Stores issue and return records of books.

Application Modules

============================================================

1. main.py

Acts as the entry point of the system.
Initializes the database and launches the main GUI.

2. main_gui.py

Contains the main user interface and navigation logic.
Provides pages for managing books, students, and issued books.
Includes options for adding, editing, deleting, searching, and exporting records.

3. db_manager.py

Implements the DatabaseManager class for handling all SQLite database operations:

Creating tables (if not present)

Adding, updating, deleting records

Issuing and returning books

Exporting data to CSV files

4. dialogs.py

Defines dialog windows for data entry and editing:

AddEditBookDialog – Add or edit book details.

AddEditStudentDialog – Add or edit student details.

Features

============================================================

Add, edit, and delete book and student records

Issue and return books with tracking

View issued books and history

Export data to CSV

Search and filter records

Local SQLite database (works offline)

Optional precompiled .exe version for faster access

Data Storage

============================================================

All data is stored locally in the library.db file.
CSV export allows external storage and reporting.

Design Notes

============================================================

Built using PyQt6 for a clean and responsive user interface

Uses SQLite for local data persistence

Modular code design for maintainability and scalability

Works on Windows, macOS, and Linux (source)

.exe file built using PyInstaller for fast startup on Windows

============================================================
🤖 AI USE NOTICE
============================================================

Certain parts of this project utilized AI assistance for organization and formatting:

• Code formatting and readability improvements — ChatGPT (OpenAI GPT-5)
• Formatting and documentation preparation for README.txt and sources.txt — ChatGPT (OpenAI GPT-5)
• Application logo and GUI window icon design — Sora AI  
  (Source: https://sora.chatgpt.com/g/gen_01k7s395nbfh48j3xqk996ghmj)

All functional logic, structure, and implementation were created and reviewed by the developer.

============================================================
xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

============================================================

Developer Information

============================================================

Developed By:
Kinshuk Aggarwal 
Chitresh 

============================================================
School:

Satluj Public School , Sector 4 , Panchkula , Haryana

============================================================

Date of Submission:
25/10/2025

============================================================
xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx