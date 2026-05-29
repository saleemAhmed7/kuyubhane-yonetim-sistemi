use kutuphane_yonetim;
CREATE TABLE Borrowing (
    borrow_id INT PRIMARY KEY IDENTITY(1,1),
    student_id INT NOT NULL,
    book_id INT NOT NULL,
    borrow_date DATE NOT NULL,
    return_date DATE NOT NULL,
    status NVARCHAR(50) NOT NULL DEFAULT 'Borrowed',
    FOREIGN KEY (student_id) REFERENCES Students(student_id),
    FOREIGN KEY (book_id) REFERENCES Books(book_id)
);

CREATE TABLE Students (
    student_id INT PRIMARY KEY IDENTITY(1,1), 
    first_name NVARCHAR(100) NOT NULL,        
    last_name NVARCHAR(100) NOT NULL,         
    email NVARCHAR(255) UNIQUE NOT NULL,      
    phone NVARCHAR(15),                       
    enrollment_date DATE NOT NULL DEFAULT GETDATE(), 
    status NVARCHAR(50) NOT NULL DEFAULT 'Active'    
);


CREATE TABLE Books (
    book_id INT PRIMARY KEY IDENTITY(1,1),
    title NVARCHAR(255) NOT NULL,
    author NVARCHAR(255) NOT NULL,
    category NVARCHAR(100) NOT NULL,
    total_copies INT NOT NULL,
    available_copies INT NOT NULL
);
CREATE TABLE Users (
    user_id INT PRIMARY KEY IDENTITY(1,1),
    username NVARCHAR(50) NOT NULL UNIQUE,
    password NVARCHAR(255) NOT NULL
); 

CREATE TABLE Fines (
    fine_id INT PRIMARY KEY IDENTITY(1,1), 
    student_id INT NOT NULL,               
    book_id INT NOT NULL,                  
    fine_amount DECIMAL(10, 2) NOT NULL,   
    fine_date DATE NOT NULL DEFAULT GETDATE(),
    status NVARCHAR(50) NOT NULL DEFAULT 'Unpaid', 
    FOREIGN KEY (student_id) REFERENCES Students(student_id), 
    FOREIGN KEY (book_id) REFERENCES Books(book_id)          
);
