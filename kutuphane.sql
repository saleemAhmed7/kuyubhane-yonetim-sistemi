CREATE DATABASE IF NOT EXISTS kutuphane_yonetim;

USE kutuphane_yonetim;

CREATE TABLE Students (
    student_id INT AUTO_INCREMENT PRIMARY KEY, 
    first_name VARCHAR(100) NOT NULL,        
    last_name VARCHAR(100) NOT NULL,         
    email VARCHAR(255) UNIQUE NOT NULL,      
    phone VARCHAR(15),                       
    enrollment_date DATE NOT NULL DEFAULT (CURDATE()), 
    status VARCHAR(50) NOT NULL DEFAULT 'Active'    
);

CREATE TABLE Books (
    book_id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    author VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL,
    total_copies INT NOT NULL,
    available_copies INT NOT NULL
);

CREATE TABLE Borrowing (
    borrow_id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    book_id INT NOT NULL,
    borrow_date DATE NOT NULL,
    return_date DATE NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'Borrowed',
    FOREIGN KEY (student_id) REFERENCES Students(student_id),
    FOREIGN KEY (book_id) REFERENCES Books(book_id)
);

CREATE TABLE Users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL
); 

CREATE TABLE Fines (
    fine_id INT AUTO_INCREMENT PRIMARY KEY, 
    student_id INT NOT NULL,               
    book_id INT NOT NULL,                  
    fine_amount DECIMAL(10, 2) NOT NULL,   
    fine_date DATE NOT NULL DEFAULT (CURDATE()),
    status VARCHAR(50) NOT NULL DEFAULT 'Unpaid', 
    FOREIGN KEY (student_id) REFERENCES Students(student_id), 
    FOREIGN KEY (book_id) REFERENCES Books(book_id)          
);

DELIMITER $$

CREATE PROCEDURE AddStudent(
    IN firstName VARCHAR(100), 
    IN lastName VARCHAR(100), 
    IN email VARCHAR(255), 
    IN phone VARCHAR(15), 
    IN enrollmentDate DATE, 
    IN status VARCHAR(50)
)
BEGIN
    INSERT INTO Students (first_name, last_name, email, phone, enrollment_date, status)
    VALUES (firstName, lastName, email, phone, enrollmentDate, status);
END $$
DELIMITER $$
CREATE PROCEDURE AddBook(
    IN title VARCHAR(255), 
    IN author VARCHAR(255), 
    IN category VARCHAR(100), 
    IN totalCopies INT, 
    IN availableCopies INT
)
BEGIN
    INSERT INTO Books (title, author, category, total_copies, available_copies)
    VALUES (title, author, category, totalCopies, availableCopies);
END $$
DELIMITER ;
CREATE PROCEDURE UpdateStudent(
    IN studentId INT, 
    IN firstName VARCHAR(100), 
    IN lastName VARCHAR(100), 
    IN email VARCHAR(255), 
    IN phone VARCHAR(15), 
    IN status VARCHAR(50)
)
BEGIN
    UPDATE Students 
    SET first_name = firstName, 
        last_name = lastName, 
        email = email, 
        phone = phone, 
        status = status
    WHERE student_id = studentId;
END $$

DELIMITER $$
CREATE PROCEDURE DeleteBook(
    IN bookId INT
)
BEGIN
    DELETE FROM Books WHERE book_id = bookId;
END$$
DELIMITER ;

DELIMITER $$
CREATE PROCEDURE UpdateBook(
    IN bookId INT, 
    IN title VARCHAR(255), 
    IN author VARCHAR(255), 
    IN category VARCHAR(100), 
    IN totalCopies INT, 
    IN availableCopies INT
)
BEGIN
    UPDATE Books 
    SET title = title, 
        author = author, 
        category = category, 
        total_copies = totalCopies, 
        available_copies = availableCopies
    WHERE book_id = bookId;
END$$
DELIMITER ;

CREATE PROCEDURE BorrowBook(
    IN studentId INT, 
    IN bookId INT, 
    IN borrowDate DATE, 
    IN returnDate DATE
)
BEGIN
    INSERT INTO Borrowing (student_id, book_id, borrow_date, return_date, status)
    VALUES (studentId, bookId, borrowDate, returnDate);

    UPDATE Books 
    SET available_copies = available_copies - 1
    WHERE book_id = bookId;
END $$

CREATE PROCEDURE ReturnBook(
    IN borrowId INT, 
    IN bookId INT
)
BEGIN
    DELETE FROM Borrowing WHERE borrow_id = borrowId;

    UPDATE Books 
    SET available_copies = available_copies + 1
    WHERE book_id = bookId;
END $$
DELIMITER $$

CREATE PROCEDURE GetAllBooks()
BEGIN
    SELECT 
        book_id, 
        title, 
        author, 
        category, 
        total_copies, 
        available_copies
    FROM Books;
END$$

DELIMITER ;

CREATE PROCEDURE AddFine(
    IN studentId INT, 
    IN bookId INT, 
    IN fineAmount DECIMAL(10, 2)
)
BEGIN
    INSERT INTO Fines (student_id, book_id, fine_amount, fine_date, status)
    VALUES (studentId, bookId, fineAmount, CURDATE(), 'Unpaid');
END $$

DELIMITER $$
CREATE PROCEDURE sp_UpdateStudent(
    IN studentId INT, 
    IN firstName VARCHAR(100), 
    IN lastName VARCHAR(100), 
    IN email VARCHAR(255), 
    IN phone VARCHAR(15), 
    IN status VARCHAR(50), 
    IN enrollmentDate DATE
)
BEGIN
    UPDATE Students 
    SET first_name = firstName, 
        last_name = lastName, 
        email = email, 
        phone = phone, 
        status = status, 
        enrollment_date = enrollmentDate
    WHERE student_id = studentId;
END$$
DELIMITER ;

DELIMITER $$
CREATE PROCEDURE sp_DeleteStudent(
    IN studentId INT
)
BEGIN
    DELETE FROM Students WHERE student_id = studentId;
END$$
DELIMITER ;

DELIMITER $$
CREATE PROCEDURE sp_LoginUser (
    IN p_username VARCHAR(50),
    IN p_password VARCHAR(255),
    OUT p_result INT
)
BEGIN
    SELECT COUNT(*) INTO p_result
    FROM Users
    WHERE username = p_username AND password = p_password;
END$$



DELIMITER ;
DELIMITER $$
CREATE PROCEDURE sp_GetTotalBooks(OUT total_books INT)
BEGIN
    SELECT IFNULL(SUM(total_copies), 0) INTO total_books FROM Books;
END $$
DELIMITER $$

DELIMITER $$
CREATE PROCEDURE GetAllStudents()
BEGIN
    SELECT 
        student_id,
        first_name,
        last_name,
        email,
        phone,
        enrollment_date,
        status
    FROM Students;
END $$
DELIMITER ;
DELIMITER $$

CREATE PROCEDURE sp_ReturnBook (
    IN BorrowId INT,
    IN BookId INT,
    IN ReturnDate DATE
)
BEGIN
    DECLARE overdueDays INT;
    DECLARE fineAmount DECIMAL(10, 2);
    DECLARE studentId INT;

    SELECT student_id INTO studentId FROM Borrowing WHERE borrow_id = BorrowId;

    DELETE FROM Borrowing WHERE borrow_id = BorrowId;

    UPDATE Books 
    SET available_copies = available_copies + 1
    WHERE book_id = BookId;

    IF CURDATE() > ReturnDate THEN
        SET overdueDays = DATEDIFF(CURDATE(), ReturnDate);
        SET fineAmount = overdueDays * 5.00; 

        INSERT INTO Fines (student_id, book_id, fine_amount, fine_date, status)
        VALUES (
            studentId, 
            BookId, 
            fineAmount, 
            CURDATE(), 
            'Unpaid'
        );
    END IF;
END$$

DELIMITER ;



DELIMITER $$
CREATE PROCEDURE GetAllBorrowings()
BEGIN
    SELECT 
        b.borrow_id, 
        s.student_id, 
        CONCAT(s.first_name, ' ', s.last_name) AS student_name, 
        bk.book_id, 
        bk.title AS book_title, 
        b.borrow_date, 
        b.return_date, 
        b.status
    FROM Borrowing b
    JOIN Students s ON b.student_id = s.student_id
    JOIN Books bk ON b.book_id = bk.book_id;
END $$
DELIMITER ;

DELIMITER $$

CREATE PROCEDURE sp_GetBorrowings(IN studentId INT)
BEGIN
    SELECT 
        b.borrow_id,
        s.student_id,
        CONCAT(s.first_name, ' ', s.last_name) AS student_name,
        bk.book_id,
        bk.title AS book_title,
        b.borrow_date,
        b.return_date,
        b.status
    FROM Borrowing b
    JOIN Students s ON b.student_id = s.student_id
    JOIN Books bk ON b.book_id = bk.book_id
    WHERE s.student_id = studentId;
END$$

DELIMITER ;

DELIMITER $$

CREATE PROCEDURE AddBorrowing(
    IN studentId INT, 
    IN bookId INT, 
    IN borrowDate DATE, 
    IN returnDate DATE
)
BEGIN
    DECLARE availableCopies INT;
    SELECT available_copies INTO availableCopies
    FROM Books
    WHERE book_id = bookId;

    IF availableCopies <= 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'No available copies for this book.';
    END IF;

    INSERT INTO Borrowing (student_id, book_id, borrow_date, return_date, status)
    VALUES (studentId, bookId, borrowDate, returnDate, 'Borrowed');

    UPDATE Books
    SET available_copies = available_copies - 1
    WHERE book_id = bookId;
END $$

DELIMITER ;

DELIMITER $$
CREATE PROCEDURE GetAvailableBooks()
BEGIN
    SELECT 
        book_id,
        title,
        author,
        category,
        available_copies
    FROM Books
    WHERE available_copies > 0;
END $$
DELIMITER ;

DELIMITER $$
CREATE PROCEDURE sp_AddStudent(
    IN firstName VARCHAR(100), 
    IN lastName VARCHAR(100), 
    IN email VARCHAR(255), 
    IN phone VARCHAR(15), 
    IN enrollmentDate DATE, 
    IN status VARCHAR(50)
)
BEGIN
    INSERT INTO Students (first_name, last_name, email, phone, enrollment_date, status)
    VALUES (firstName, lastName, email, phone, enrollmentDate, status);
END$$
DELIMITER ;


DELIMITER $$
CREATE PROCEDURE sp_GetTotalStudents(OUT total_students INT)
BEGIN
    SELECT COUNT(*) INTO total_students FROM Students;
END $$
DELIMITER $$

DELIMITER $$
CREATE PROCEDURE sp_GetActiveBorrowings(OUT active_borrowings INT)
BEGIN
    SELECT COUNT(*) INTO active_borrowings FROM Borrowing WHERE return_date >= CURDATE();
END $$
DELIMITER $$

DELIMITER $$
CREATE PROCEDURE sp_GetUnpaidFines(OUT unpaid_fines INT)
BEGIN
    SELECT COUNT(*) INTO unpaid_fines FROM Fines WHERE status = 'Unpaid';
END $$
DELIMITER $$

DELIMITER $$
CREATE TRIGGER tg_check_available_copies
BEFORE INSERT ON Borrowing
FOR EACH ROW
BEGIN
    DECLARE available INT;
    SELECT available_copies INTO available
    FROM Books
    WHERE book_id = NEW.book_id;

    IF available < 1 THEN
        SIGNAL SQLSTATE '45000' 
        SET MESSAGE_TEXT = 'No copies available for this book!';
    END IF;
END$$
DELIMITER ;

DELIMITER $$
CREATE TRIGGER tg_update_copies_after_borrow
AFTER INSERT ON Borrowing
FOR EACH ROW
BEGIN
    UPDATE Books 
    SET available_copies = available_copies - 1
    WHERE book_id = NEW.book_id;
END$$
DELIMITER ;

DELIMITER $$
CREATE TRIGGER tg_update_copies_after_return
AFTER DELETE ON Borrowing
FOR EACH ROW
BEGIN
    UPDATE Books 
    SET available_copies = available_copies + 1
    WHERE book_id = OLD.book_id;
END$$
DELIMITER ;

ALTER TABLE Borrowing
DROP FOREIGN KEY borrowing_ibfk_1;

ALTER TABLE Borrowing
ADD CONSTRAINT borrowing_ibfk_1
FOREIGN KEY (student_id) REFERENCES Students(student_id)
ON DELETE CASCADE;



