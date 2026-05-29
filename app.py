import os
from datetime import date, timedelta
from functools import wraps

import mysql.connector
from flask import Flask, flash, redirect, render_template, request, session, url_for, jsonify
from mysql.connector import Error, errorcode
from werkzeug.utils import secure_filename
import csv
import io
import re
import pandas as pd


app = Flask(__name__)
app.secret_key = "library-management-secret-key"
# Development/runtime helpers: enable template auto-reload and disable static caching during development
app.config.setdefault('TEMPLATES_AUTO_RELOAD', True)
app.jinja_env.auto_reload = True
app.config.setdefault('SEND_FILE_MAX_AGE_DEFAULT', 0)

# Explicitly configure session cookies to prevent collisions and modernize security settings
app.config.update(
    SESSION_COOKIE_NAME='kutuphane_session', # Isolate cookie name from other local apps
    SESSION_COOKIE_SECURE=False,            # Permit cookie usage over local HTTP connection
    SESSION_COOKIE_HTTPONLY=True,            # Prevent client-side script access for security
    SESSION_COOKIE_SAMESITE='Lax',            # Ensure secure and robust same-site cookie shipping
    SESSION_COOKIE_PATH='/',                 # Scope cookie globally
)
UPLOAD_FOLDER = os.path.join("static", "images", "profiles")
ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}


def load_env_file(path=".env"):
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as env_file:
        for raw_line in env_file:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env_file()


def current_db_config():
    return {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "3306")),
        "user": os.getenv("DB_USER", "root"),
        "password": os.getenv("DB_PASSWORD", "saleem123@"),
        "database": os.getenv("DB_NAME", "kutuphane_yonetimi"),
    }


DB_CONFIG = current_db_config()

LANGUAGES = {
    "en": {
        "name": "English",
        "dir": "ltr",
        "app_title": "Library Management System",
        "student_portal": "Student Portal",
        "dashboard": "Dashboard",
        "students": "Students",
        "books": "Books",
        "borrowing": "Borrowing",
        "fines": "Fines",
        "mysql_setup": "MySQL Setup",
        "logout": "Logout",
        "book_catalog": "Book Catalog",
        "my_borrowings": "My Borrowings",
        "mysql_connected": "MySQL connected",
        "mysql_needs_setup": "MySQL needs setup",
        "library_management": "Library Management",
        "due_soon": "Due Soon",
        "no_notifications": "No urgent notifications.",
        "admin": "Admin",
        "secure_access": "Secure access",
        "login_title": "Library Management Login",
        "login_hint": "Sign in with your desktop system admin account.",
        "username": "Username",
        "password": "Password",
        "login": "Login",
        "need_student_account": "Need a student account?",
        "create_one": "Create one",
        "new_student": "New Student",
        "library_account": "Library account",
        "student_registration": "Student registration",
        "create_account": "Create your account",
        "register_hint": "Your account and student profile will be saved in MySQL.",
        "first_name": "First Name",
        "last_name": "Last Name",
        "email": "Email",
        "phone": "Phone",
        "confirm_password": "Confirm Password",
        "register": "Register",
        "already_have_account": "Already have an account?",
        "today_overview": "Today overview",
        "dashboard_intro_title": "Manage students, books, and borrowing from one clean workspace.",
        "dashboard_intro_text": "Inventory availability, due books, and recent activity are always one click away.",
        "new_borrow": "New Borrow",
        "total_books": "Total Books",
        "total_students": "Total Students",
        "active_borrowings": "Active Borrowings",
        "unpaid_fines": "Unpaid Fines",
        "inventory": "Inventory",
        "book_categories": "Book Categories",
        "available": "available",
        "no_book_categories": "No book categories yet.",
        "health": "Health",
        "system_snapshot": "System Snapshot",
        "available_copies": "Available copies",
        "borrowed_books": "Borrowed books",
        "overdue_books": "Overdue books",
        "activity": "Activity",
        "recent_borrowing_history": "Recent Borrowing History",
        "manage": "Manage",
        "student": "Student",
        "book": "Book",
        "borrow_date": "Borrow Date",
        "due_date": "Due Date",
        "status": "Status",
        "no_borrowing_records": "No borrowing records yet.",
        "student_portal_label": "Student portal",
        "available_books": "Available books",
        "books_available": "books available",
        "search_title_author_category": "Search title, author, category",
        "search": "Search",
        "title": "Title",
        "author": "Author",
        "category": "Category",
        "action": "Action",
        "borrow": "Borrow",
        "borrow_confirm": "Borrow this book for 14 days?",
        "no_available_books": "No available books found.",
        "my_borrowed_books": "My borrowed books",
        "catalog": "Catalog",
        "history": "History",
        "return_date": "Return Date",
        "no_my_borrowings": "You have not borrowed any books yet.",
        "my_fines": "My fines",
        "amount": "Amount",
        "date": "Date",
        "no_my_fines": "No fines on your account.",
        "account": "Account",
        "edit_account": "Edit Account",
        "profile": "Profile",
        "profile_photo": "Profile Photo",
        "full_name": "Full Name",
        "save_changes": "Save Changes",
        "total_accounts": "Total Accounts",
        "admin_accounts": "Admin Accounts",
        "student_accounts": "Student Accounts",
        "new_accounts": "New Accounts",
        "chat_greeting": "Hello! I am EduBot AI — ask me about books, dataset, or exams.",
        "placeholder_message": "Type a message... (Enter to send)",
        "button_return": "Return",
        "button_return_book": "Return Book",
        "button_delete": "Delete",
        "button_close": "Close",
        "button_send": "Send",
        "button_confirm": "Confirm",
        "button_cancel": "Cancel",
        "enter_identifier": "Enter serial number, title, or student id to return",
        "processing_return": "Processing return...",
        "network_error": "Network error. Please try again.",
        "unexpected_response": "Unexpected response from server.",
        "returned": "Returned",
        "borrowed": "Borrowed",
    },
    "tr": {
        "name": "Türkçe",
        "dir": "ltr",
        "app_title": "Kütüphane Yönetim Sistemi",
        "student_portal": "Öğrenci Portalı",
        "dashboard": "Panel",
        "students": "Öğrenciler",
        "books": "Kitaplar",
        "borrowing": "Ödünç Alma",
        "fines": "Cezalar",
        "mysql_setup": "MySQL Ayarları",
        "logout": "Çıkış",
        "book_catalog": "Kitap Kataloğu",
        "my_borrowings": "Ödünç Aldıklarım",
        "mysql_connected": "MySQL bağlı",
        "mysql_needs_setup": "MySQL ayarı gerekli",
        "library_management": "Kütüphane Yönetimi",
        "due_soon": "Yakında Teslim",
        "no_notifications": "Acil bildirim yok.",
        "admin": "Yönetici",
        "secure_access": "Güvenli giriş",
        "login_title": "Kütüphane Yönetimi Girişi",
        "login_hint": "Masaüstü sistem yönetici hesabınızla giriş yapın.",
        "username": "Kullanıcı adı",
        "password": "Şifre",
        "login": "Giriş",
        "need_student_account": "Öğrenci hesabına mı ihtiyacınız var?",
        "create_one": "Hesap oluştur",
        "new_student": "Yeni Öğrenci",
        "library_account": "Kütüphane hesabı",
        "student_registration": "Öğrenci kaydı",
        "create_account": "Hesabınızı oluşturun",
        "register_hint": "Hesabınız ve öğrenci profiliniz MySQL'e kaydedilecek.",
        "first_name": "Ad",
        "last_name": "Soyad",
        "email": "E-posta",
        "phone": "Telefon",
        "confirm_password": "Şifreyi onayla",
        "register": "Kayıt ol",
        "already_have_account": "Zaten hesabınız var mı?",
        "today_overview": "Bugünün özeti",
        "dashboard_intro_title": "Öğrencileri, kitapları ve ödünç işlemlerini tek panelden yönetin.",
        "dashboard_intro_text": "Stok durumu, yaklaşan teslimler ve son hareketler her zaman elinizin altında.",
        "new_borrow": "Yeni Ödünç",
        "total_books": "Toplam Kitap",
        "total_students": "Toplam Öğrenci",
        "active_borrowings": "Aktif Ödünçler",
        "unpaid_fines": "Ödenmemiş Cezalar",
        "inventory": "Envanter",
        "book_categories": "Kitap Kategorileri",
        "available": "mevcut",
        "no_book_categories": "Henüz kitap kategorisi yok.",
        "health": "Durum",
        "system_snapshot": "Sistem Özeti",
        "available_copies": "Mevcut kopyalar",
        "borrowed_books": "Ödünç kitaplar",
        "overdue_books": "Geciken kitaplar",
        "activity": "Hareketler",
        "recent_borrowing_history": "Son Ödünç Geçmişi",
        "manage": "Yönet",
        "student": "Öğrenci",
        "book": "Kitap",
        "borrow_date": "Ödünç Tarihi",
        "due_date": "Teslim Tarihi",
        "status": "Durum",
        "no_borrowing_records": "Henüz ödünç kaydı yok.",
        "student_portal_label": "Öğrenci portalı",
        "available_books": "Mevcut kitaplar",
        "books_available": "kitap mevcut",
        "search_title_author_category": "Başlık, yazar, kategori ara",
        "search": "Ara",
        "title": "Başlık",
        "author": "Yazar",
        "category": "Kategori",
        "action": "İşlem",
        "borrow": "Ödünç al",
        "borrow_confirm": "Bu kitabı 14 günlüğüne ödünç almak istiyor musunuz?",
        "no_available_books": "Mevcut kitap bulunamadı.",
        "my_borrowed_books": "Ödünç aldığım kitaplar",
        "catalog": "Katalog",
        "history": "Geçmiş",
        "return_date": "Teslim Tarihi",
        "no_my_borrowings": "Henüz kitap ödünç almadınız.",
        "my_fines": "Cezalarım",
        "amount": "Tutar",
        "date": "Tarih",
        "no_my_fines": "Hesabınızda ceza yok.",
        "account": "Hesap",
        "edit_account": "Hesabı Düzenle",
        "profile": "Profil",
        "profile_photo": "Profil Fotoğrafı",
        "full_name": "Ad Soyad",
        "save_changes": "Değişiklikleri Kaydet",
        "total_accounts": "Toplam Hesap",
        "admin_accounts": "Yönetici Hesapları",
        "student_accounts": "Öğrenci Hesapları",
        "new_accounts": "Yeni Hesaplar",
    },
    "ar": {
        "name": "العربية",
        "dir": "rtl",
        "app_title": "نظام إدارة المكتبة",
        "student_portal": "بوابة الطالب",
        "dashboard": "لوحة التحكم",
        "students": "الطلاب",
        "books": "الكتب",
        "borrowing": "الاستعارات",
        "fines": "الغرامات",
        "mysql_setup": "إعدادات MySQL",
        "logout": "تسجيل الخروج",
        "book_catalog": "فهرس الكتب",
        "my_borrowings": "استعاراتي",
        "mysql_connected": "MySQL متصل",
        "mysql_needs_setup": "MySQL يحتاج إعداد",
        "library_management": "إدارة المكتبة",
        "due_soon": "قريب التسليم",
        "no_notifications": "لا توجد تنبيهات عاجلة.",
        "admin": "المدير",
        "secure_access": "دخول آمن",
        "login_title": "تسجيل دخول نظام المكتبة",
        "login_hint": "سجل الدخول بحساب نظام سطح المكتب.",
        "username": "اسم المستخدم",
        "password": "كلمة المرور",
        "login": "دخول",
        "need_student_account": "تحتاج حساب طالب؟",
        "create_one": "أنشئ حساب",
        "new_student": "طالب جديد",
        "library_account": "حساب المكتبة",
        "student_registration": "تسجيل طالب",
        "create_account": "أنشئ حسابك",
        "register_hint": "سيتم حفظ حسابك وبيانات الطالب في MySQL.",
        "first_name": "الاسم الأول",
        "last_name": "اسم العائلة",
        "email": "البريد الإلكتروني",
        "phone": "الهاتف",
        "confirm_password": "تأكيد كلمة المرور",
        "register": "تسجيل",
        "already_have_account": "لديك حساب بالفعل؟",
        "today_overview": "نظرة اليوم",
        "dashboard_intro_title": "إدارة الطلاب والكتب والاستعارات من مكان واحد.",
        "dashboard_intro_text": "توفر النسخ، الكتب المستحقة، وآخر النشاطات أمامك دائما.",
        "new_borrow": "استعارة جديدة",
        "total_books": "إجمالي الكتب",
        "total_students": "إجمالي الطلاب",
        "active_borrowings": "الاستعارات النشطة",
        "unpaid_fines": "الغرامات غير المدفوعة",
        "inventory": "المخزون",
        "book_categories": "تصنيفات الكتب",
        "available": "متاح",
        "no_book_categories": "لا توجد تصنيفات كتب بعد.",
        "health": "الحالة",
        "system_snapshot": "ملخص النظام",
        "available_copies": "النسخ المتاحة",
        "borrowed_books": "الكتب المستعارة",
        "overdue_books": "الكتب المتأخرة",
        "activity": "النشاط",
        "recent_borrowing_history": "آخر سجل استعارات",
        "manage": "إدارة",
        "student": "الطالب",
        "book": "الكتاب",
        "borrow_date": "تاريخ الاستعارة",
        "due_date": "تاريخ الإرجاع",
        "status": "الحالة",
        "no_borrowing_records": "لا توجد سجلات استعارة بعد.",
        "student_portal_label": "بوابة الطالب",
        "available_books": "الكتب المتاحة",
        "books_available": "كتاب متاح",
        "search_title_author_category": "ابحث بالعنوان أو المؤلف أو التصنيف",
        "search": "بحث",
        "title": "العنوان",
        "author": "المؤلف",
        "category": "التصنيف",
        "action": "الإجراء",
        "borrow": "استعارة",
        "borrow_confirm": "هل تريد استعارة هذا الكتاب لمدة 14 يوم؟",
        "no_available_books": "لا توجد كتب متاحة.",
        "my_borrowed_books": "كتبي المستعارة",
        "catalog": "الفهرس",
        "history": "السجل",
        "return_date": "تاريخ الإرجاع",
        "no_my_borrowings": "لم تستعر أي كتب بعد.",
        "my_fines": "غراماتي",
        "amount": "المبلغ",
        "date": "التاريخ",
        "no_my_fines": "لا توجد غرامات على حسابك.",
        "account": "الحساب",
        "edit_account": "تعديل الحساب",
        "profile": "الملف الشخصي",
        "profile_photo": "صورة الحساب",
        "full_name": "الاسم الكامل",
        "save_changes": "حفظ التغييرات",
        "total_accounts": "إجمالي الحسابات",
        "admin_accounts": "حسابات الأدمن",
        "student_accounts": "حسابات الطلاب",
        "new_accounts": "الحسابات الجديدة",
    },
}


def save_env_config(form):
    values = {
        "DB_HOST": form.get("host", "localhost").strip() or "localhost",
        "DB_PORT": form.get("port", "3306").strip() or "3306",
        "DB_USER": form.get("user", "root").strip() or "root",
        "DB_PASSWORD": form.get("password", ""),
        "DB_NAME": form.get("database", "kutuphane_yonetimi").strip() or "kutuphane_yonetimi",
    }
    with open(".env", "w", encoding="utf-8") as env_file:
        for key, value in values.items():
            env_file.write(f"{key}={value}\n")
    os.environ.update(values)
    DB_CONFIG.update(current_db_config())


def get_db():
    return mysql.connector.connect(**DB_CONFIG)


def get_server_connection():
    config = DB_CONFIG.copy()
    config.pop("database", None)
    return mysql.connector.connect(**config)


def ensure_schema():
    conn = get_server_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{DB_CONFIG['database']}` "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        cursor.execute(f"USE `{DB_CONFIG['database']}`")
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS Students (
                student_id INT AUTO_INCREMENT PRIMARY KEY,
                first_name VARCHAR(100) NOT NULL,
                last_name VARCHAR(100) NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                phone VARCHAR(20),
                enrollment_date DATE NOT NULL DEFAULT (CURDATE()),
                status VARCHAR(50) NOT NULL DEFAULT 'Active'
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS Books (
                book_id INT AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                author VARCHAR(255) NOT NULL,
                category VARCHAR(100) NOT NULL,
                total_copies INT NOT NULL DEFAULT 1,
                available_copies INT NOT NULL DEFAULT 1,
                serial_number INT UNIQUE,
                shelf_location VARCHAR(50),
                order_position INT,
                CHECK (total_copies >= 0),
                CHECK (available_copies >= 0)
            )
            """
        )
        # Ensure columns exist for older schemas
        cursor.execute("SHOW COLUMNS FROM Books LIKE 'serial_number'")
        if cursor.fetchone() is None:
            cursor.execute("ALTER TABLE Books ADD COLUMN serial_number INT UNIQUE NULL")
        cursor.execute("SHOW COLUMNS FROM Books LIKE 'shelf_location'")
        if cursor.fetchone() is None:
            cursor.execute("ALTER TABLE Books ADD COLUMN shelf_location VARCHAR(50) NULL")
        cursor.execute("SHOW COLUMNS FROM Books LIKE 'order_position'")
        if cursor.fetchone() is None:
            cursor.execute("ALTER TABLE Books ADD COLUMN order_position INT NULL")
        cursor.execute("SHOW COLUMNS FROM Books LIKE 'image_url'")
        if cursor.fetchone() is None:
            cursor.execute("ALTER TABLE Books ADD COLUMN image_url VARCHAR(255) NULL")
        cursor.execute("SHOW COLUMNS FROM Books LIKE 'description'")
        if cursor.fetchone() is None:
            cursor.execute("ALTER TABLE Books ADD COLUMN description TEXT NULL")
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS Borrowing (
                borrow_id INT AUTO_INCREMENT PRIMARY KEY,
                student_id INT NOT NULL,
                book_id INT NOT NULL,
                borrow_date DATE NOT NULL,
                return_date DATE NOT NULL,
                status VARCHAR(50) NOT NULL DEFAULT 'Borrowed',
                returned_at DATE NULL,
                FOREIGN KEY (student_id) REFERENCES Students(student_id) ON DELETE CASCADE,
                FOREIGN KEY (book_id) REFERENCES Books(book_id) ON DELETE CASCADE
            )
            """
        )
        # ensure returned_at exists for older schemas
        cursor.execute("SHOW COLUMNS FROM Borrowing LIKE 'returned_at'")
        if cursor.fetchone() is None:
            cursor.execute("ALTER TABLE Borrowing ADD COLUMN returned_at DATE NULL")
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS Users (
                user_id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) NOT NULL UNIQUE,
                password VARCHAR(255) NOT NULL,
                role VARCHAR(30) NOT NULL DEFAULT 'Admin',
                student_id INT NULL,
                full_name VARCHAR(150),
                email VARCHAR(255),
                avatar VARCHAR(255),
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        user_columns = {
            "role": "ALTER TABLE Users ADD COLUMN role VARCHAR(30) NOT NULL DEFAULT 'Admin'",
            "student_id": "ALTER TABLE Users ADD COLUMN student_id INT NULL",
            "full_name": "ALTER TABLE Users ADD COLUMN full_name VARCHAR(150)",
            "email": "ALTER TABLE Users ADD COLUMN email VARCHAR(255)",
            "avatar": "ALTER TABLE Users ADD COLUMN avatar VARCHAR(255)",
            "created_at": "ALTER TABLE Users ADD COLUMN created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP",
        }
        for column, statement in user_columns.items():
            cursor.execute(f"SHOW COLUMNS FROM Users LIKE '{column}'")
            if cursor.fetchone() is None:
                cursor.execute(statement)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS Fines (
                fine_id INT AUTO_INCREMENT PRIMARY KEY,
                student_id INT NOT NULL,
                book_id INT NOT NULL,
                fine_amount DECIMAL(10, 2) NOT NULL,
                fine_date DATE NOT NULL DEFAULT (CURDATE()),
                status VARCHAR(50) NOT NULL DEFAULT 'Unpaid',
                FOREIGN KEY (student_id) REFERENCES Students(student_id) ON DELETE CASCADE,
                FOREIGN KEY (book_id) REFERENCES Books(book_id) ON DELETE CASCADE
            )
            """
        )
        cursor.execute(
            """
            INSERT IGNORE INTO Users (username, password, role, full_name, email)
            VALUES ('admin', 'admin', 'Admin', 'Library Admin', 'admin@library.local')
            """
        )
        # Chat history tables for admin and student (separate storage)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS AdminChat (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NULL,
                message TEXT NOT NULL,
                sender VARCHAR(16) NOT NULL,
                meta JSON NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS StudentChat (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NULL,
                message TEXT NOT NULL,
                sender VARCHAR(16) NOT NULL,
                meta JSON NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        # Import log table to track processed CSV files and avoid re-import
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS ImportLog (
                id INT AUTO_INCREMENT PRIMARY KEY,
                file_name VARCHAR(255) NOT NULL UNIQUE,
                imported_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                rows INT NOT NULL DEFAULT 0
            )
            """
        )
        conn.commit()
        # Auto-generate serial numbers and defaults for existing rows
        cursor.execute("SELECT book_id, serial_number, category FROM Books")
        rows = cursor.fetchall()
        max_serial = 1000
        for r in rows:
            bid = r[0]
            s = r[1]
            cat = r[2] or 'A'
            if s is None:
                max_serial += 1
                cursor.execute("UPDATE Books SET serial_number=%s WHERE book_id=%s", (max_serial, bid))
            # set default shelf_location if null
            cursor.execute("SELECT shelf_location, order_position FROM Books WHERE book_id=%s", (bid,))
            curvals = cursor.fetchone()
            if curvals and (curvals[0] is None or curvals[1] is None):
                shelf = (cat.strip()[:1].upper() if cat else 'A') + '-01'
                order_pos = bid
                cursor.execute("UPDATE Books SET shelf_location=%s, order_position=%s WHERE book_id=%s", (shelf, order_pos, bid))
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def import_csv_archive():
    """Read all CSV files in /archive, insert into Books, avoid duplicates, create categories, and assign serial numbers."""
    archive_dir = os.path.join(os.getcwd(), 'archive')
    if not os.path.isdir(archive_dir):
        return {'imported': 0, 'files': 0}
    files = [f for f in os.listdir(archive_dir) if f.lower().endswith('.csv')]
    if not files:
        return {'imported': 0, 'files': 0}

    conn = get_db()
    cursor = conn.cursor()
    imported_total = 0
    try:
        for fname in files:
            # skip already imported files
            cursor.execute('SELECT id FROM ImportLog WHERE file_name=%s', (fname,))
            if cursor.fetchone():
                continue
            path = os.path.join(archive_dir, fname)
            try:
                df = pd.read_csv(path, dtype=str, encoding='utf-8', on_bad_lines='skip')
            except Exception:
                try:
                    df = pd.read_csv(path, dtype=str, encoding='latin-1', on_bad_lines='skip')
                except Exception:
                    continue

            cols = {c.lower().strip(): c for c in df.columns}
            def get_field(row, keys):
                for k in keys:
                    if k in cols:
                        v = row[cols[k]]
                        if pd.isna(v):
                            return None
                        return str(v).strip()
                return None

            rows_added = 0
            for _, r in df.iterrows():
                title = get_field(r, ['title', 'book', 'name']) or get_field(r, ['başlık', 'isim'])
                author = get_field(r, ['author', 'yazar', 'writer']) or 'Bilinmiyor'
                category = get_field(r, ['category', 'kategori', 'genre', 'type']) or ''
                image = get_field(r, ['image', 'image_url', 'cover'])
                desc = get_field(r, ['description', 'summary', 'explanation'])
                copies_raw = get_field(r, ['copies', 'total_copies', 'adet', 'count'])
                try:
                    copies = int(float(copies_raw)) if copies_raw else 1
                except Exception:
                    copies = 1

                if not title:
                    continue

                # normalize for duplicate detection
                tnorm = re.sub(r"\s+"," ", title).strip()
                anorm = re.sub(r"\s+"," ", author).strip()

                # check for existing book by exact title+author
                cursor.execute('SELECT book_id, total_copies, available_copies FROM Books WHERE title=%s AND author=%s', (tnorm, anorm))
                existing = cursor.fetchone()
                if existing:
                    # update copies
                    book_id, tot, avail = existing
                    new_tot = (tot or 0) + copies
                    new_avail = (avail or 0) + copies
                    cursor.execute('UPDATE Books SET total_copies=%s, available_copies=%s WHERE book_id=%s', (new_tot, new_avail, book_id))
                    rows_added += 1
                    imported_total += 1
                    continue

                # generate next serial
                cursor.execute('SELECT COALESCE(MAX(serial_number), 1000) FROM Books')
                max_row = cursor.fetchone()
                max_serial = max_row[0] if max_row and max_row[0] is not None else 1000
                next_serial = int(max_serial) + 1

                shelf = (category.strip()[:1].upper() if category else 'A') + '-01'

                cursor.execute(
                    'INSERT INTO Books (title, author, category, total_copies, available_copies, serial_number, shelf_location, order_position, image_url, description) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                    (tnorm, anorm, category or 'Genel', copies, copies, next_serial, shelf, None, image, desc),
                )
                rows_added += 1
                imported_total += 1

            # record import log
            cursor.execute('INSERT INTO ImportLog (file_name, rows) VALUES (%s, %s)', (fname, rows_added))
            conn.commit()
    finally:
        cursor.close()
        conn.close()

    return {'imported': imported_total, 'files': len(files)}


def test_connection(config):
    server_config = config.copy()
    server_config.pop("database", None)
    conn = mysql.connector.connect(**server_config)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()[0]
        cursor.execute("SHOW DATABASES")
        databases = [row[0] for row in cursor.fetchall()]
        return version, databases
    finally:
        cursor.close()
        conn.close()


def db_query(query, params=None, fetchone=False, commit=False):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(query, params or ())
        if commit:
            conn.commit()
            return cursor.lastrowid
        if fetchone:
            return cursor.fetchone()
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()


def handle_db_errors(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        try:
            return view(*args, **kwargs)
        except Error as exc:
            return render_template("db_error.html", error=exc, config=DB_CONFIG), 500

    return wrapped


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin_id"):
            if request.is_json or request.path.startswith('/api'):
                return jsonify({"error": "unauthorized", "message": "Oturumunuzun süresi doldu. Lütfen tekrar giriş yapın."}), 401
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin_id"):
            if request.is_json or request.path.startswith('/api'):
                return jsonify({"error": "unauthorized", "message": "Oturumunuzun süresi doldu. Lütfen tekrar giriş yapın."}), 401
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login", next=request.path))
        if session.get("role") != "Admin":
            if request.is_json or request.path.startswith('/api'):
                return jsonify({"error": "forbidden", "message": "Bu işlem için yetkiniz bulunmamaktadır."}), 403
            flash("This page is only for the library admin.", "danger")
            return redirect(url_for("catalog"))
        return view(*args, **kwargs)

    return wrapped


def translate(key):
    # Force Turkish-only UI: always return Turkish translations
    return LANGUAGES.get("tr", {}).get(key, key)


def allowed_image(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


@app.route("/language/<lang>")
def set_language(lang):
    if lang in LANGUAGES:
        session["lang"] = lang
    return redirect(request.referrer or url_for("login"))


def trigger_exists(trigger_name):
    row = db_query(
        """
        SELECT COUNT(*) AS total
        FROM information_schema.TRIGGERS
        WHERE TRIGGER_SCHEMA = %s AND TRIGGER_NAME = %s
        """,
        (DB_CONFIG["database"], trigger_name),
        fetchone=True,
    )
    return bool(row and row["total"])


def sync_inventory():
    db_query(
        """
        UPDATE Books bk
        LEFT JOIN (
            SELECT book_id, COUNT(*) AS active_borrows
            FROM Borrowing
            WHERE status = 'Borrowed'
            GROUP BY book_id
        ) br ON br.book_id = bk.book_id
        SET bk.available_copies = GREATEST(bk.total_copies - COALESCE(br.active_borrows, 0), 0)
        """,
        commit=True,
    )


@app.route("/login", methods=["GET", "POST"])
@handle_db_errors
def login():
    if session.get("admin_id"):
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = db_query(
            "SELECT user_id, username, role, student_id, avatar FROM Users WHERE username=%s AND password=%s",
            (username, password),
            fetchone=True,
        )
        if user:
            session["admin_id"] = user["user_id"]
            session["admin_username"] = user["username"]
            session["role"] = user.get("role") or "Admin"
            session["student_id"] = user.get("student_id")
            session["avatar"] = user.get("avatar")
            flash("Welcome back.", "success")
            if session["role"] == "Student":
                return redirect(url_for("catalog"))
            return redirect(request.args.get("next") or url_for("dashboard"))
        flash("Invalid username or password.", "danger")

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
@handle_db_errors
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("register"))

        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT user_id FROM Users WHERE username=%s", (username,))
            if cursor.fetchone():
                flash("Username already exists.", "danger")
                conn.rollback()
                return redirect(url_for("register"))

            cursor.execute("SELECT student_id FROM Students WHERE email=%s", (request.form["email"],))
            if cursor.fetchone():
                flash("A student account with this email already exists.", "danger")
                conn.rollback()
                return redirect(url_for("register"))

            cursor.execute(
                """
                INSERT INTO Students (first_name, last_name, email, phone, enrollment_date, status)
                VALUES (%s, %s, %s, %s, CURDATE(), 'Active')
                """,
                (
                    request.form["first_name"],
                    request.form["last_name"],
                    request.form["email"],
                    request.form.get("phone") or None,
                ),
            )
            student_id = cursor.lastrowid
            cursor.execute(
                """
                INSERT INTO Users (username, password, role, student_id, full_name, email)
                VALUES (%s, %s, 'Student', %s, %s, %s)
                """,
                (
                    username,
                    password,
                    student_id,
                    f"{request.form['first_name']} {request.form['last_name']}",
                    request.form["email"],
                ),
            )
            conn.commit()
            flash("Account created successfully. You can now log in.", "success")
            return redirect(url_for("login"))
        except Error:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()

    return render_template("register.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


@app.route("/account", methods=["GET", "POST"])
@login_required
@handle_db_errors
def account():
    user_id = session.get("admin_id")
    user = db_query(
        "SELECT user_id, username, password, role, student_id, full_name, email, avatar FROM Users WHERE user_id=%s",
        (user_id,),
        fetchone=True,
    )
    if not user:
        session.clear()
        flash("Account not found. Please log in again.", "danger")
        return redirect(url_for("login"))

    student = None
    if user.get("student_id"):
        student = db_query("SELECT * FROM Students WHERE student_id=%s", (user["student_id"],), fetchone=True)

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip() or user["password"]
        avatar = user.get("avatar")

        existing = db_query(
            "SELECT user_id FROM Users WHERE username=%s AND user_id<>%s",
            (username, user_id),
            fetchone=True,
        )
        if existing:
            flash("Username already exists.", "danger")
            return redirect(url_for("account"))

        image = request.files.get("avatar")
        if image and image.filename:
            if not allowed_image(image.filename):
                flash("Please upload a valid image file.", "danger")
                return redirect(url_for("account"))
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            extension = secure_filename(image.filename).rsplit(".", 1)[1].lower()
            filename = f"user_{user_id}.{extension}"
            image.save(os.path.join(UPLOAD_FOLDER, filename))
            avatar = f"images/profiles/{filename}"

        db_query(
            """
            UPDATE Users
            SET username=%s, password=%s, full_name=%s, email=%s, avatar=%s
            WHERE user_id=%s
            """,
            (username, password, full_name or None, email or None, avatar, user_id),
            commit=True,
        )

        if student:
            names = full_name.split(" ", 1)
            first_name = names[0] if names else student["first_name"]
            last_name = names[1] if len(names) > 1 else student["last_name"]
            db_query(
                """
                UPDATE Students
                SET first_name=%s, last_name=%s, email=%s, phone=%s
                WHERE student_id=%s
                """,
                (
                    first_name,
                    last_name,
                    email or student["email"],
                    request.form.get("phone") or student.get("phone"),
                    student["student_id"],
                ),
                commit=True,
            )

        session["admin_username"] = username
        session["avatar"] = avatar
        flash("Account updated successfully.", "success")
        return redirect(url_for("account"))

    return render_template("account.html", user=user, student=student)


@app.route("/catalog")
@login_required
@handle_db_errors
def catalog():
    if session.get("role") != "Student":
        return redirect(url_for("dashboard"))

    search = request.args.get("q", "").strip()
    query = "SELECT * FROM Books WHERE available_copies > 0"
    params = []
    if search:
        query += " AND (title LIKE %s OR author LIKE %s OR category LIKE %s)"
        like = f"%{search}%"
        params.extend([like, like, like])
    query += " ORDER BY category, title"
    rows = db_query(query, tuple(params))

    # organize by category
    categories = {}
    for r in rows:
        cat = (r.get('category') or 'Uncategorized').strip()
        categories.setdefault(cat, []).append(r)

    # prepare ordered category list
    ordered = [(cat, categories[cat]) for cat in sorted(categories.keys())]
    return render_template("catalog.html", categories=ordered, search=search)


@app.route('/categories')
@login_required
@handle_db_errors
def categories_page():
    if session.get('role') != 'Student':
        return redirect(url_for('dashboard'))
    rows = db_query("SELECT category, COUNT(*) AS count FROM Books GROUP BY category ORDER BY category")
    return render_template('categories.html', categories=rows)


@app.route('/categories/<path:category_name>')
@login_required
@handle_db_errors
def category_detail(category_name):
    if session.get('role') != 'Student':
        return redirect(url_for('dashboard'))
    q = request.args.get('q','').strip()
    params = [category_name]
    query = "SELECT * FROM Books WHERE category = %s"
    if q:
        # search by title or serial
        if q.startswith('#') and q[1:].isdigit():
            query = "SELECT * FROM Books WHERE category = %s AND serial_number = %s"
            params = [category_name, int(q[1:])]
        else:
            like = f"%{q}%"
            query += " AND (title LIKE %s OR CAST(serial_number AS CHAR) LIKE %s)"
            params.extend([like, like])
    rows = db_query(query + " ORDER BY title", tuple(params))
    return render_template('category_detail.html', category=category_name, books=rows, search=q)


@app.route('/api/book-info')
@login_required
@handle_db_errors
def api_book_info():
    q = (request.args.get('q') or '').strip()
    if not q:
        return jsonify({'error':'missing query'}), 400
    # if serial like #1001 or numeric
    if q.startswith('#') and q[1:].isdigit():
        sn = int(q[1:])
        row = db_query('SELECT * FROM Books WHERE serial_number=%s', (sn,), fetchone=True)
        if not row:
            return jsonify({'q':q,'count':0,'results':[]})
        return jsonify({'q':q,'count':1,'results':[row]})
    if q.isdigit():
        row = db_query('SELECT * FROM Books WHERE serial_number=%s', (int(q),), fetchone=True)
        if row:
            return jsonify({'q':q,'count':1,'results':[row]})
    like = f"%{q}%"
    rows = db_query("SELECT * FROM Books WHERE title LIKE %s OR author LIKE %s OR category LIKE %s LIMIT 10", (like, like, like))
    return jsonify({'q':q,'count':len(rows),'results':rows})


@app.route("/api/book-bot")
@login_required
@handle_db_errors
def book_bot_api():
    """Simple search API over the local CSV dataset. Returns JSON results.

    Query param: q (string)
    """
    q = (request.args.get("q") or "").strip().lower()
    dataset_path = os.path.join("archive", "TurkishBookDataSet.csv")
    results = []
    if not os.path.exists(dataset_path):
        return jsonify({"error": "Dataset not found."}), 404

    try:
        with open(dataset_path, "r", encoding="utf-8", errors="ignore") as f:
            reader = csv.DictReader(f)
            for row in reader:
                title = (row.get("name") or row.get("title") or "").strip()
                author = (row.get("author") or "").strip()
                explanation = (row.get("explanation") or row.get("description") or "").strip()
                img = (row.get("book_img") or row.get("image") or "").strip()
                haystack = " ".join([title, author, explanation]).lower()
                if not q or q in haystack:
                    # create a short snippet for explanation
                    snippet = explanation
                    if len(snippet) > 400:
                        snippet = snippet[:400].rsplit(".", 1)[0] + "..."
                    results.append({
                        "title": title,
                        "author": author,
                        "explanation": snippet,
                        "image": img,
                    })
                    if len(results) >= 10:
                        break
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

    return jsonify({"q": q, "count": len(results), "results": results})


### Chatbot DB-backed endpoints and helpers (student/admin separation)

ARABIC_INDIC_MAP = str.maketrans({
    '٠':'0','١':'1','٢':'2','٣':'3','٤':'4','٥':'5','٦':'6','٧':'7','٨':'8','٩':'9',
    '۰':'0','۱':'1','۲':'2','۳':'3','۴':'4','۵':'5','۶':'6','۷':'7','۸':'8','۹':'9'
})

def _normalize_digits(s: str):
    return (s or '').translate(ARABIC_INDIC_MAP)

def _extract_first_number(q: str):
    if not q:
        return None
    q2 = _normalize_digits(q)
    m = re.search(r"(\d{2,})", q2)
    if m:
        try:
            return int(m.group(1))
        except Exception:
            return None
    return None

def _detect_lang(q: str):
    # System is Turkish-only
    return 'tr'

def _format_book_row(row):
    return {
        'title': row.get('title'),
        'serial_number': row.get('serial_number'),
        'category': row.get('category'),
        'shelf_location': row.get('shelf_location'),
        'order_position': row.get('order_position'),
        'available_copies': row.get('available_copies'),
        'image_url': row.get('image_url'),
        'description': row.get('description'),
        'book_id': row.get('book_id')
    }


def _search_csv_archive(q, limit=10):
    """Search CSV files in the archive folder for matching books.
    Returns list of dicts with same keys as _format_book_row.
    """
    results = []
    qnorm = (q or '').strip().lower()
    num = _extract_first_number(q)
    archive_dir = os.path.join(os.getcwd(), 'archive')
    if not os.path.isdir(archive_dir):
        return results
    files = [f for f in os.listdir(archive_dir) if f.lower().endswith('.csv')]
    for fname in files:
        path = os.path.join(archive_dir, fname)
        try:
            df = pd.read_csv(path, dtype=str, encoding='utf-8', on_bad_lines='skip')
        except Exception:
            try:
                df = pd.read_csv(path, dtype=str, encoding='latin-1', on_bad_lines='skip')
            except Exception:
                continue
        # normalize columns
        cols = {c.lower().strip(): c for c in df.columns}
        def get_field(row, keys):
            for k in keys:
                if k in cols:
                    return (row[cols[k]] if pd.notna(row[cols[k]]) else None)
            return None

        for _, r in df.iterrows():
            title = get_field(r, ['title', 'book', 'name']) or ''
            author = get_field(r, ['author', 'yazar', 'writer']) or ''
            category = get_field(r, ['category', 'kategori', 'genre']) or ''
            serial = get_field(r, ['serial', 'serial_number', 'id', 'no']) or None
            if serial is not None:
                # try to extract digits
                m = re.search(r"(\d{2,})", str(serial))
                if m:
                    try:
                        serial = int(m.group(1))
                    except Exception:
                        serial = None
                else:
                    serial = None
            # search logic
            matched = False
            if num and serial and num == serial:
                matched = True
            elif qnorm and (qnorm in str(title).lower() or qnorm in str(author).lower() or qnorm in str(category).lower()):
                matched = True
            if matched:
                item = {
                    'title': title,
                    'serial_number': serial,
                    'category': category,
                    'shelf_location': get_field(r, ['shelf', 'shelf_location']) or None,
                    'order_position': get_field(r, ['order', 'order_position']) or None,
                    'available_copies': None,
                    'image_url': get_field(r, ['image', 'image_url', 'cover']) or None,
                    'description': get_field(r, ['description', 'explanation', 'summary']) or None,
                    'book_id': None,
                }
                results.append(item)
                if len(results) >= limit:
                    return results
    return results


@app.route('/api/chat/history')
@login_required
@handle_db_errors
def api_chat_history():
    scope = (request.args.get('scope') or 'student').lower()
    if scope == 'admin':
        if session.get('role') != 'Admin':
            return jsonify({'error':'forbidden'}), 403
        uid = session.get('admin_id')
        rows = db_query('SELECT * FROM AdminChat WHERE user_id=%s ORDER BY id ASC', (uid,))
        return jsonify({'scope':'admin','count':len(rows),'rows':rows})
    else:
        # student scope
        sid = session.get('student_id')
        rows = db_query('SELECT * FROM StudentChat WHERE user_id=%s ORDER BY id ASC', (sid,))
        return jsonify({'scope':'student','count':len(rows),'rows':rows})


@app.route('/api/chat/delete', methods=['POST'])
@login_required
@handle_db_errors
def api_chat_delete():
    scope = (request.form.get('scope') or 'student').lower()
    if scope == 'admin':
        if session.get('role') != 'Admin':
            return jsonify({'error':'forbidden'}), 403
        uid = session.get('admin_id')
        db_query('DELETE FROM AdminChat WHERE user_id=%s', (uid,), commit=True)
        return jsonify({'ok':True,'scope':'admin'})
    else:
        sid = session.get('student_id')
        db_query('DELETE FROM StudentChat WHERE user_id=%s', (sid,), commit=True)
        return jsonify({'ok':True,'scope':'student'})


@app.route('/api/chatbook')
@login_required
@handle_db_errors
def api_chatbook():
    q = (request.args.get('q') or '').strip()
    if not q:
        return jsonify({'error':'missing query'}), 400
    num = _extract_first_number(q)
    if num:
        row = db_query('SELECT * FROM Books WHERE serial_number=%s AND available_copies>0', (num,), fetchone=True)
        if row:
            return jsonify({'q':q,'lang':_detect_lang(q),'count':1,'results':[_format_book_row(row)]})
        # fallback to CSVs
        csv_results = _search_csv_archive(q, limit=5)
        if csv_results:
            return jsonify({'q':q,'lang':_detect_lang(q),'count':len(csv_results),'results':csv_results})
        return jsonify({'q':q,'lang':_detect_lang(q),'count':0,'results':[]})
    like = f"%{q}%"
    rows = db_query('SELECT * FROM Books WHERE available_copies>0 AND (title LIKE %s OR author LIKE %s OR category LIKE %s) LIMIT 10', (like, like, like))
    if rows:
        return jsonify({'q':q,'lang':_detect_lang(q),'count':len(rows),'results':[_format_book_row(r) for r in rows]})
    # fallback to CSVs when DB empty
    csv_results = _search_csv_archive(q, limit=10)
    return jsonify({'q':q,'lang':_detect_lang(q),'count':len(csv_results),'results':csv_results})


@app.route('/api/chatbook-admin')
@login_required
@admin_required
@handle_db_errors
def api_chatbook_admin():
    q = (request.args.get('q') or '').strip()
    action = (request.args.get('action') or '').strip().lower()
    if action == 'duplicates':
        rows = db_query('SELECT title, author, COUNT(*) AS cnt FROM Books GROUP BY title, author HAVING cnt>1 ORDER BY cnt DESC')
        return jsonify({'action':'duplicates','count':len(rows),'rows':rows})
    if action == 'categories':
        rows = db_query('SELECT category, COUNT(*) AS count FROM Books GROUP BY category ORDER BY count DESC')
        return jsonify({'action':'categories','count':len(rows),'rows':rows})
    if action == 'import_status':
        try:
            files = len([f for f in os.listdir(os.path.join(os.getcwd(),'archive')) if f.lower().endswith('.csv')])
        except Exception:
            files = 0
        totals = db_query('SELECT COUNT(*) AS titles, COALESCE(SUM(total_copies),0) AS copies FROM Books', fetchone=True)
        return jsonify({'action':'import_status','csv_files':files,'titles':totals.get('titles',0),'copies':totals.get('copies',0)})
    if not q:
        return jsonify({'error':'missing query or action'}), 400
    num = _extract_first_number(q)
    if num:
        row = db_query('SELECT * FROM Books WHERE serial_number=%s', (num,), fetchone=True)
        if row:
            return jsonify({'q':q,'lang':_detect_lang(q),'count':1,'results':[_format_book_row(row)]})
        csv_results = _search_csv_archive(q, limit=6)
        if csv_results:
            return jsonify({'q':q,'lang':_detect_lang(q),'count':len(csv_results),'results':csv_results})
        return jsonify({'q':q,'lang':_detect_lang(q),'count':0,'results':[]})
    like = f"%{q}%"
    rows = db_query('SELECT * FROM Books WHERE title LIKE %s OR author LIKE %s OR category LIKE %s LIMIT 40', (like, like, like))
    if rows:
        return jsonify({'q':q,'lang':_detect_lang(q),'count':len(rows),'results':[_format_book_row(r) for r in rows]})
    csv_results = _search_csv_archive(q, limit=40)
    return jsonify({'q':q,'lang':_detect_lang(q),'count':len(csv_results),'results':csv_results})


@app.route('/api/chat/save', methods=['POST'])
@login_required
@handle_db_errors
def api_chat_save():
    """Persist a chat message for the current user and scope.
    Expects JSON: { scope: 'admin'|'student', sender: 'user'|'bot', message: '...' }
    """
    data = request.get_json() or {}
    scope = (data.get('scope') or 'student').lower()
    sender = data.get('sender') or 'user'
    message = data.get('message') or ''
    if scope == 'admin':
        if session.get('role') != 'Admin':
            return jsonify({'error':'forbidden'}), 403
        uid = session.get('admin_id')
        db_query('INSERT INTO AdminChat (user_id, message, sender) VALUES (%s,%s,%s)', (uid, message, sender), commit=True)
        return jsonify({'ok':True})
    else:
        sid = session.get('student_id')
        db_query('INSERT INTO StudentChat (user_id, message, sender) VALUES (%s,%s,%s)', (sid, message, sender), commit=True)
        return jsonify({'ok':True})


@app.route('/api/return-book', methods=['POST'])
@login_required
@handle_db_errors
def api_return_book():
    """Return a book by serial number, title, or student id.
    JSON input: { identifier: '...', type: 'serial'|'title'|'student' (optional) }
    """
    data = request.get_json() or {}
    identifier = (data.get('identifier') or '').strip()
    if not identifier:
        return jsonify({'error':'missing identifier'}), 400
    typ = (data.get('type') or '').lower()
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        # Determine caller permissions
        is_admin = session.get('role') == 'Admin'
        student_scope = session.get('student_id') if not is_admin else None

        # Try serial detection first regardless of type
        num = _extract_first_number(identifier)
        borrow_record = None
        if num:
            # find the book by serial
            cursor.execute('SELECT * FROM Books WHERE serial_number=%s', (num,))
            book = cursor.fetchone()
            if book:
                # find active borrowing
                if is_admin:
                    cursor.execute("SELECT * FROM Borrowing WHERE book_id=%s AND status='Borrowed' ORDER BY borrow_id DESC LIMIT 1", (book['book_id'],))
                else:
                    cursor.execute("SELECT * FROM Borrowing WHERE book_id=%s AND student_id=%s AND status='Borrowed' ORDER BY borrow_id DESC LIMIT 1", (book['book_id'], student_scope))
                borrow_record = cursor.fetchone()
        # try by title
        if not borrow_record and (typ == 'title' or not num):
            like = f"%{identifier}%"
            if is_admin:
                cursor.execute("SELECT br.* FROM Borrowing br JOIN Books bk ON bk.book_id=br.book_id WHERE bk.title LIKE %s AND br.status='Borrowed' ORDER BY br.borrow_id DESC LIMIT 1", (like,))
            else:
                cursor.execute("SELECT br.* FROM Borrowing br JOIN Books bk ON bk.book_id=br.book_id WHERE bk.title LIKE %s AND br.student_id=%s AND br.status='Borrowed' ORDER BY br.borrow_id DESC LIMIT 1", (like, student_scope))
            borrow_record = cursor.fetchone() or borrow_record

        # try by student id
        if not borrow_record and (typ == 'student' or identifier.isdigit()):
            sid = int(identifier) if identifier.isdigit() else None
            if sid:
                if is_admin:
                    cursor.execute("SELECT * FROM Borrowing WHERE student_id=%s AND status='Borrowed' ORDER BY borrow_id DESC LIMIT 1", (sid,))
                else:
                    # students can only return their own
                    if sid != student_scope:
                        return jsonify({'error':'forbidden'}), 403
                    cursor.execute("SELECT * FROM Borrowing WHERE student_id=%s AND status='Borrowed' ORDER BY borrow_id DESC LIMIT 1", (sid,))
                borrow_record = cursor.fetchone() or borrow_record

        if not borrow_record:
            return jsonify({'error':'not_found','message':'No active borrowing found for provided identifier. If the book exists only in CSVs, import it first.'}), 404

        # perform return
        cursor.execute("SELECT * FROM Borrowing WHERE borrow_id=%s FOR UPDATE", (borrow_record['borrow_id'],))
        rec = cursor.fetchone()
        if not rec or rec['status'] == 'Returned':
            return jsonify({'error':'already_returned'}), 400

        cursor.execute("UPDATE Borrowing SET status='Returned', returned_at = CURDATE() WHERE borrow_id=%s", (rec['borrow_id'],))
        cursor.execute("UPDATE Books SET available_copies = available_copies + 1 WHERE book_id=%s", (rec['book_id'],))
        # fine calculation
        if rec.get('return_date') and date.today() > rec['return_date']:
            overdue_days = (date.today() - rec['return_date']).days
            fine_amount = overdue_days * 5.00
            cursor.execute(
                "INSERT INTO Fines (student_id, book_id, fine_amount, fine_date, status) VALUES (%s, %s, %s, CURDATE(), 'Unpaid')",
                (rec['student_id'], rec['book_id'], fine_amount),
            )
        conn.commit()
        return jsonify({'ok':True,'message':'Book returned and inventory updated.'})
    except Error as e:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


@app.route('/api/return-borrowing', methods=['POST'])
@login_required
@handle_db_errors
def api_return_borrowing():
    data = request.get_json() or {}
    borrow_id = data.get('borrow_id')
    if not borrow_id:
        return jsonify({'error':'missing borrow_id'}), 400
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute('SELECT * FROM Borrowing WHERE borrow_id=%s FOR UPDATE', (borrow_id,))
        rec = cursor.fetchone()
        if not rec:
            return jsonify({'error':'not_found'}), 404
        # permission check
        if session.get('role') != 'Admin' and rec['student_id'] != session.get('student_id'):
            return jsonify({'error':'forbidden'}), 403

        if rec['status'] == 'Returned':
            return jsonify({'error':'already_returned'}), 400

        cursor.execute('UPDATE Borrowing SET status=%s WHERE borrow_id=%s', ('Returned', borrow_id))
        cursor.execute('UPDATE Books SET available_copies = available_copies + 1 WHERE book_id=%s', (rec['book_id'],))
        # fines
        if rec.get('return_date') and date.today() > rec['return_date']:
            overdue_days = (date.today() - rec['return_date']).days
            fine_amount = overdue_days * 5.00
            cursor.execute(
                "INSERT INTO Fines (student_id, book_id, fine_amount, fine_date, status) VALUES (%s, %s, %s, CURDATE(), 'Unpaid')",
                (rec['student_id'], rec['book_id'], fine_amount),
            )
        conn.commit()
        return jsonify({'ok':True,'message':'Book returned.'})
    except Error:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


@app.route("/my-borrowings")
@login_required
@handle_db_errors
def my_borrowings():
    if session.get("role") != "Student":
        return redirect(url_for("dashboard"))

    rows = db_query(
        """
        SELECT br.*, bk.title AS book_title, bk.author
        FROM Borrowing br
        JOIN Books bk ON bk.book_id = br.book_id
        WHERE br.student_id = %s
        ORDER BY br.borrow_id DESC
        """,
        (session.get("student_id"),),
    )
    fines = db_query(
        """
        SELECT f.*, b.title AS book_title
        FROM Fines f
        JOIN Books b ON b.book_id = f.book_id
        WHERE f.student_id = %s
        ORDER BY f.fine_id DESC
        """,
        (session.get("student_id"),),
    )
    return render_template("my_borrowings.html", borrowings=rows, fines=fines)


@app.route("/borrow/book/<int:book_id>", methods=["POST"])
@login_required
@handle_db_errors
def borrow_from_catalog(book_id):
    if session.get("role") != "Student":
        return redirect(url_for("dashboard"))

    student_id = session.get("student_id")
    borrow_date = date.today()
    return_date = borrow_date + timedelta(days=14)
    database_handles_borrow_inventory = trigger_exists("tg_update_copies_after_borrow")

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT available_copies FROM Books WHERE book_id=%s FOR UPDATE", (book_id,))
        book = cursor.fetchone()
        if not book or book["available_copies"] <= 0:
            flash("This book is not available right now.", "danger")
            conn.rollback()
            return redirect(url_for("catalog"))

        cursor.execute(
            """
            SELECT borrow_id FROM Borrowing
            WHERE student_id=%s AND book_id=%s AND status='Borrowed'
            """,
            (student_id, book_id),
        )
        if cursor.fetchone():
            flash("You already borrowed this book.", "warning")
            conn.rollback()
            return redirect(url_for("catalog"))

        cursor.execute(
            """
            INSERT INTO Borrowing (student_id, book_id, borrow_date, return_date, status)
            VALUES (%s, %s, %s, %s, 'Borrowed')
            """,
            (student_id, book_id, borrow_date, return_date),
        )
        if not database_handles_borrow_inventory:
            cursor.execute("UPDATE Books SET available_copies = available_copies - 1 WHERE book_id=%s", (book_id,))
        conn.commit()
        flash("Book borrowed successfully. Return date is set for 14 days later.", "success")
    except Error:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for("my_borrowings"))


def get_stats():
    stats = {}
    stats["students"] = db_query("SELECT COUNT(*) AS total FROM Students", fetchone=True)["total"]
    stats["titles"] = db_query("SELECT COUNT(*) AS total FROM Books", fetchone=True)["total"]
    stats["copies"] = db_query("SELECT COALESCE(SUM(total_copies), 0) AS total FROM Books", fetchone=True)["total"]
    stats["available"] = db_query("SELECT COALESCE(SUM(available_copies), 0) AS total FROM Books", fetchone=True)["total"]
    stats["borrowed"] = db_query("SELECT COUNT(*) AS total FROM Borrowing WHERE status = 'Borrowed'", fetchone=True)["total"]
    stats["unpaid_fines"] = db_query("SELECT COUNT(*) AS total FROM Fines WHERE status = 'Unpaid'", fetchone=True)["total"]
    stats["accounts"] = db_query("SELECT COUNT(*) AS total FROM Users", fetchone=True)["total"]
    stats["admin_accounts"] = db_query("SELECT COUNT(*) AS total FROM Users WHERE role='Admin'", fetchone=True)["total"]
    stats["student_accounts"] = db_query("SELECT COUNT(*) AS total FROM Users WHERE role='Student'", fetchone=True)["total"]
    stats["new_accounts"] = db_query(
        "SELECT COUNT(*) AS total FROM Users WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)",
        fetchone=True,
    )["total"]
    stats["overdue"] = db_query(
        "SELECT COUNT(*) AS total FROM Borrowing WHERE status = 'Borrowed' AND return_date < CURDATE()",
        fetchone=True,
    )["total"]
    return stats


@app.context_processor
def inject_globals():
    today = date.today()
    db_online = True
    # Force Turkish site-wide
    lang = 'tr'
    try:
        notifications = db_query(
            """
            SELECT br.borrow_id, br.return_date, bk.title, s.first_name, s.last_name
            FROM Borrowing br
            JOIN Books bk ON bk.book_id = br.book_id
            JOIN Students s ON s.student_id = br.student_id
            WHERE br.status = 'Borrowed' AND br.return_date <= %s
            ORDER BY br.return_date ASC
            LIMIT 6
            """,
            (today + timedelta(days=2),),
        )
    except Error:
        db_online = False
        notifications = []
    current_user = None
    if session.get("admin_id"):
        try:
            current_user = db_query(
                "SELECT user_id, username, role, full_name, email, avatar FROM Users WHERE user_id=%s",
                (session.get("admin_id"),),
                fetchone=True,
            )
        except Error:
            current_user = None
    return {
        "today": today,
        "notifications": notifications,
        "db_online": db_online,
        "db_name": DB_CONFIG["database"],
        "languages": {"tr": LANGUAGES.get("tr", {})},
        "current_lang": lang,
        "page_dir": LANGUAGES.get("tr", {}).get("dir", "ltr"),
        "t": translate,
        "current_user": current_user,
    }


@app.route("/")
@admin_required
@handle_db_errors
def dashboard():
    stats = get_stats()
    recent_borrowings = db_query(
        """
        SELECT br.borrow_id, br.borrow_date, br.return_date, br.status,
               CONCAT(s.first_name, ' ', s.last_name) AS student_name,
               bk.title AS book_title
        FROM Borrowing br
        JOIN Students s ON s.student_id = br.student_id
        JOIN Books bk ON bk.book_id = br.book_id
        ORDER BY br.borrow_id DESC
        LIMIT 8
        """
    )
    category_data = db_query(
        """
        SELECT category, COUNT(*) AS titles, COALESCE(SUM(total_copies), 0) AS copies
        FROM Books
        GROUP BY category
        ORDER BY copies DESC
        LIMIT 6
        """
    )
    return render_template("index.html", stats=stats, recent_borrowings=recent_borrowings, category_data=category_data)


@app.route("/students")
@admin_required
@handle_db_errors
def students():
    search = request.args.get("q", "").strip()
    if search:
        like = f"%{search}%"
        rows = db_query(
            """
            SELECT * FROM Students
            WHERE first_name LIKE %s OR last_name LIKE %s OR email LIKE %s OR phone LIKE %s OR status LIKE %s
            ORDER BY student_id DESC
            """,
            (like, like, like, like, like),
        )
    else:
        rows = db_query("SELECT * FROM Students ORDER BY student_id DESC")
    return render_template("students.html", students=rows, search=search)


@app.route("/students/add", methods=["POST"])
@admin_required
@handle_db_errors
def add_student():
    db_query(
        """
        INSERT INTO Students (first_name, last_name, email, phone, enrollment_date, status)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            request.form["first_name"],
            request.form["last_name"],
            request.form["email"],
            request.form.get("phone") or None,
            request.form["enrollment_date"],
            request.form["status"],
        ),
        commit=True,
    )
    flash("Student added successfully.", "success")
    return redirect(url_for("students"))


@app.route("/students/<int:student_id>/edit", methods=["POST"])
@admin_required
@handle_db_errors
def edit_student(student_id):
    db_query(
        """
        UPDATE Students
        SET first_name=%s, last_name=%s, email=%s, phone=%s, enrollment_date=%s, status=%s
        WHERE student_id=%s
        """,
        (
            request.form["first_name"],
            request.form["last_name"],
            request.form["email"],
            request.form.get("phone") or None,
            request.form["enrollment_date"],
            request.form["status"],
            student_id,
        ),
        commit=True,
    )
    flash("Student updated successfully.", "success")
    return redirect(url_for("students"))


@app.route("/students/<int:student_id>/delete", methods=["POST"])
@admin_required
@handle_db_errors
def delete_student(student_id):
    db_query("DELETE FROM Students WHERE student_id=%s", (student_id,), commit=True)
    flash("Student deleted successfully.", "warning")
    return redirect(url_for("students"))


@app.route("/books")
@admin_required
@handle_db_errors
def books():
    search = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    categories = db_query("SELECT DISTINCT category FROM Books ORDER BY category")
    query = "SELECT * FROM Books WHERE 1=1"
    params = []
    if search:
        query += " AND (title LIKE %s OR author LIKE %s OR category LIKE %s)"
        like = f"%{search}%"
        params.extend([like, like, like])
    if category:
        query += " AND category = %s"
        params.append(category)
    query += " ORDER BY book_id DESC"
    rows = db_query(query, tuple(params))
    return render_template("books.html", books=rows, categories=categories, search=search, selected_category=category)


@app.route("/books/add", methods=["POST"])
@admin_required
@handle_db_errors
def add_book():
    total = int(request.form["total_copies"])
    available = int(request.form.get("available_copies") or total)
    # generate next serial number
    row = db_query('SELECT COALESCE(MAX(serial_number), 1000) AS mx FROM Books', fetchone=True)
    next_serial = (row.get('mx') if row and row.get('mx') else 1000) + 1
    db_query(
        """
        INSERT INTO Books (title, author, category, total_copies, available_copies, serial_number)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (request.form["title"], request.form["author"], request.form["category"], total, min(available, total), next_serial),
        commit=True,
    )
    flash("Book added successfully.", "success")
    return redirect(url_for("books"))


@app.route("/books/<int:book_id>/edit", methods=["POST"])
@admin_required
@handle_db_errors
def edit_book(book_id):
    total = int(request.form["total_copies"])
    available = min(int(request.form["available_copies"]), total)
    db_query(
        """
        UPDATE Books
        SET title=%s, author=%s, category=%s, total_copies=%s, available_copies=%s
        WHERE book_id=%s
        """,
        (request.form["title"], request.form["author"], request.form["category"], total, available, book_id),
        commit=True,
    )
    flash("Book updated successfully.", "success")
    return redirect(url_for("books"))


@app.route("/books/<int:book_id>/delete", methods=["POST"])
@admin_required
@handle_db_errors
def delete_book(book_id):
    db_query("DELETE FROM Books WHERE book_id=%s", (book_id,), commit=True)
    flash("Book deleted successfully.", "warning")
    return redirect(url_for("books"))


@app.route("/borrowing")
@app.route("/borrow", methods=["GET"])
@admin_required
@handle_db_errors
def borrowing():
    search = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    query = """
        SELECT br.*, CONCAT(s.first_name, ' ', s.last_name) AS student_name,
               s.email, bk.title AS book_title, bk.author
        FROM Borrowing br
        JOIN Students s ON s.student_id = br.student_id
        JOIN Books bk ON bk.book_id = br.book_id
        WHERE 1=1
    """
    params = []
    if search:
        like = f"%{search}%"
        query += " AND (s.first_name LIKE %s OR s.last_name LIKE %s OR s.email LIKE %s OR bk.title LIKE %s OR bk.author LIKE %s)"
        params.extend([like, like, like, like, like])
    if status:
        query += " AND br.status = %s"
        params.append(status)
    query += " ORDER BY br.borrow_id DESC"
    rows = db_query(query, tuple(params))
    students_list = db_query("SELECT student_id, first_name, last_name FROM Students WHERE status='Active' ORDER BY first_name")
    available_books = db_query("SELECT book_id, title, available_copies FROM Books WHERE available_copies > 0 ORDER BY title")
    return render_template(
        "borrowing.html",
        borrowings=rows,
        students=students_list,
        books=available_books,
        search=search,
        selected_status=status,
    )


@app.route("/borrowing/add", methods=["POST"])
@app.route("/borrow", methods=["POST"])
@admin_required
@handle_db_errors
def add_borrowing():
    student_id = int(request.form["student_id"])
    book_id = int(request.form["book_id"])
    borrow_date = request.form["borrow_date"]
    return_date = request.form["return_date"]
    database_handles_borrow_inventory = trigger_exists("tg_update_copies_after_borrow")

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT available_copies FROM Books WHERE book_id=%s FOR UPDATE", (book_id,))
        book = cursor.fetchone()
        if not book or book["available_copies"] <= 0:
            flash("No available copies for this book.", "danger")
            conn.rollback()
            return redirect(url_for("borrowing"))

        cursor.execute(
            """
            INSERT INTO Borrowing (student_id, book_id, borrow_date, return_date, status)
            VALUES (%s, %s, %s, %s, 'Borrowed')
            """,
            (student_id, book_id, borrow_date, return_date),
        )
        if not database_handles_borrow_inventory:
            cursor.execute("UPDATE Books SET available_copies = available_copies - 1 WHERE book_id=%s", (book_id,))
        conn.commit()
        flash("Book borrowed successfully.", "success")
    except Error:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for("borrowing"))


@app.route("/borrowing/<int:borrow_id>/return", methods=["POST"])
@app.route("/return/<int:borrow_id>", methods=["POST"])
@admin_required
@handle_db_errors
def return_book(borrow_id):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM Borrowing WHERE borrow_id=%s FOR UPDATE", (borrow_id,))
        record = cursor.fetchone()
        if not record or record["status"] == "Returned":
            flash("Borrowing record is already closed.", "info")
            conn.rollback()
            return redirect(url_for("borrowing"))

        cursor.execute("UPDATE Borrowing SET status='Returned' WHERE borrow_id=%s", (borrow_id,))
        cursor.execute("UPDATE Books SET available_copies = available_copies + 1 WHERE book_id=%s", (record["book_id"],))
        if record["return_date"] and date.today() > record["return_date"]:
            overdue_days = (date.today() - record["return_date"]).days
            fine_amount = overdue_days * 5.00
            cursor.execute(
                """
                INSERT INTO Fines (student_id, book_id, fine_amount, fine_date, status)
                VALUES (%s, %s, %s, CURDATE(), 'Unpaid')
                """,
                (record["student_id"], record["book_id"], fine_amount),
            )
        conn.commit()
        flash("Book returned and inventory updated.", "success")
    except Error:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for("borrowing"))


@app.route("/return")
@admin_required
@handle_db_errors
def return_page():
    return redirect(url_for("borrowing", status="Borrowed"))


@app.route("/fines")
@admin_required
@handle_db_errors
def fines():
    status = request.args.get("status", "Unpaid").strip()
    query = """
        SELECT f.*, CONCAT(s.first_name, ' ', s.last_name) AS student_name,
               s.email, b.title AS book_title
        FROM Fines f
        JOIN Students s ON s.student_id = f.student_id
        JOIN Books b ON b.book_id = f.book_id
        WHERE 1=1
    """
    params = []
    if status:
        query += " AND f.status = %s"
        params.append(status)
    query += " ORDER BY f.fine_id DESC"
    rows = db_query(query, tuple(params))
    totals = db_query(
        """
        SELECT
            COALESCE(SUM(CASE WHEN status='Unpaid' THEN fine_amount ELSE 0 END), 0) AS unpaid_amount,
            COUNT(CASE WHEN status='Unpaid' THEN 1 END) AS unpaid_count,
            COUNT(*) AS total_count
        FROM Fines
        """,
        fetchone=True,
    )
    return render_template("fines.html", fines=rows, totals=totals, selected_status=status)


@app.route("/fines/<int:fine_id>/pay", methods=["POST"])
@admin_required
@handle_db_errors
def pay_fine(fine_id):
    db_query("UPDATE Fines SET status='Paid' WHERE fine_id=%s", (fine_id,), commit=True)
    flash("Fine marked as paid.", "success")
    return redirect(url_for("fines"))


@app.route("/edit", methods=["POST"])
@admin_required
@handle_db_errors
def edit_dispatch():
    entity = request.form.get("entity", "").strip().lower()
    entity_id = request.form.get("id", type=int)
    if entity == "student" and entity_id:
        return edit_student(entity_id)
    if entity == "book" and entity_id:
        return edit_book(entity_id)
    flash("Invalid edit request.", "danger")
    return redirect(url_for("dashboard"))


@app.route("/delete", methods=["POST"])
@admin_required
@handle_db_errors
def delete_dispatch():
    entity = request.form.get("entity", "").strip().lower()
    entity_id = request.form.get("id", type=int)
    if entity == "student" and entity_id:
        return delete_student(entity_id)
    if entity == "book" and entity_id:
        return delete_book(entity_id)
    flash("Invalid delete request.", "danger")
    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    try:
        ensure_schema()
        sync_inventory()
        print(f"Connected to MySQL database `{DB_CONFIG['database']}` on {DB_CONFIG['host']}:{DB_CONFIG['port']}")
        try:
            import_csv_archive()
            print('CSV archive import completed (if files were present).')
        except Exception:
            print('CSV import encountered an error or no files to import.')
    except Error as exc:
        if getattr(exc, "errno", None) == errorcode.ER_ACCESS_DENIED_ERROR:
            print("MySQL access denied. Update DB_USER / DB_PASSWORD in .env, then run python app.py again.")
        else:
            print(f"MySQL setup warning: {exc}")

    # Development: prefer livereload when available for frontend auto-refresh (HTML/CSS/JS)
    app.debug = True
    try:
        from livereload import Server

        server = Server(app.wsgi_app)
        # Watch templates and static assets for changes
        server.watch('templates/')
        server.watch('static/')
        # Also watch python files in project root
        server.watch('*.py')
        print("Starting livereload server on http://127.0.0.1:5000 — templates/static will auto-refresh")
        server.serve(host='127.0.0.1', port=5000, debug=True)
    except Exception:
        # Fallback to Flask builtin reloader
        app.run(host="127.0.0.1", port=5000, debug=True, use_reloader=True)
