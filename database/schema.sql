
CREATE TABLE Library (
    library_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    address VARCHAR(255) NOT NULL,
    phone_number VARCHAR(20),
    email VARCHAR(100) UNIQUE
);
CREATE TABLE Book (
    book_id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    author VARCHAR(100) NOT NULL,
    isbn VARCHAR(17) NOT NULL UNIQUE, 
    publication_year INT,
    category VARCHAR(50),
    
    CONSTRAINT check_publication_year CHECK (publication_year > 1000)
);
CREATE TABLE User_Role (
    role_id SERIAL PRIMARY KEY,
    role_name VARCHAR(50) NOT NULL UNIQUE --> 'Admin', 'Member'
);
CREATE TABLE App_User (
    user_id SERIAL PRIMARY KEY,
    library_id INT NOT NULL, 
    role_id INT NOT NULL, 
    name VARCHAR(100) NOT NULL,
    address VARCHAR(255) NOT NULL,
    date_of_birth DATE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL, 
    password_hash VARCHAR(255) NOT NULL, 
    is_active BOOLEAN NOT NULL DEFAULT TRUE, 
    
    CONSTRAINT fk_user_library
        FOREIGN KEY (library_id)
        REFERENCES Library (library_id)
        ON DELETE RESTRICT,
    CONSTRAINT fk_user_role
        FOREIGN KEY (role_id)
        REFERENCES User_Role (role_id)
        ON DELETE RESTRICT
);
CREATE TABLE Item (
    item_id SERIAL PRIMARY KEY,
    book_id INT NOT NULL,
    library_id INT NOT NULL, 
    item_condition VARCHAR(50) NOT NULL,
    shelf_mark VARCHAR(50) NOT NULL, 
    
    CONSTRAINT fk_item_book
        FOREIGN KEY (book_id)
        REFERENCES Book (book_id)
        ON DELETE CASCADE, 
    CONSTRAINT fk_item_library
        FOREIGN KEY (library_id)
        REFERENCES Library (library_id)
        ON DELETE RESTRICT,
    CONSTRAINT unique_shelf_mark_per_library
        UNIQUE (library_id, shelf_mark),
    CONSTRAINT check_item_condition
        CHECK (item_condition IN ('good', 'average', 'worn', 'new', 'pending scrap'))
);
CREATE TABLE Loan (
    loan_id SERIAL PRIMARY KEY,
    item_id INT NOT NULL,
    user_id INT NOT NULL,
    loan_date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    due_date DATE NOT NULL, --> A kolcsonzesi idot a Node.js szamolja majd
    return_date TIMESTAMP WITH TIME ZONE,
    fine_paid NUMERIC(10, 2) DEFAULT 0.00,
    
    CONSTRAINT fk_loan_item
        FOREIGN KEY (item_id)
        REFERENCES Item (item_id)
        ON DELETE RESTRICT,
    CONSTRAINT fk_loan_user
        FOREIGN KEY (user_id)
        REFERENCES App_User (user_id)
        ON DELETE RESTRICT,
    CONSTRAINT check_due_date
        CHECK (due_date >= loan_date::DATE),
    CONSTRAINT check_fine_positive
        CHECK (fine_paid >= 0.00)
);
CREATE TABLE Reservation (
    reservation_id SERIAL PRIMARY KEY,
    book_id INT NOT NULL, 
    user_id INT NOT NULL,
    queue_number INT NOT NULL,
    reservation_date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expiry_date DATE,
    status VARCHAR(50) NOT NULL DEFAULT 'pending', 

    CONSTRAINT fk_reservation_book
        FOREIGN KEY (book_id)
        REFERENCES Book (book_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_reservation_user
        FOREIGN KEY (user_id)
        REFERENCES App_User (user_id)
        ON DELETE CASCADE,
    CONSTRAINT unique_active_reservation
        UNIQUE (book_id, user_id), 
    CONSTRAINT unique_queue_number_per_book
        UNIQUE (book_id, queue_number),
    CONSTRAINT check_reservation_status
        CHECK (status IN ('pending', 'ready', 'expired', 'fulfilled'))
);


--Indexek kereshez majd
CREATE INDEX idx_book_author ON Book (author); --szerzore keress
CREATE INDEX idx_book_title ON Book (title); --cimre keress
CREATE INDEX idx_user_name ON App_User (name); --username keress
CREATE INDEX idx_item_shelf_mark ON Item (shelf_mark); --raktari keszlet keress

CREATE INDEX idx_loan_active --berlesi statuszhoz kapcsolodo
ON Loan (item_id)
WHERE return_date IS NULL;

CREATE INDEX idx_loan_due_date ON Loan (due_date); --lejaro kolcsonzesek lekerdezese

CREATE INDEX idx_reservation_queue --varolista konyv cimekre
ON Reservation (book_id, queue_number);