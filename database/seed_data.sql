---Insert adatok---
INSERT INTO user_role (role_id, role_name) VALUES
    (1, 'Admin'),
    (2, 'Member')
ON CONFLICT (role_id) DO NOTHING;
---
INSERT INTO library (library_id, name, address) VALUES
    (1, 'Central Library', 'Budapest, Kossuth Lajos tér 1.')
ON CONFLICT (library_id) DO NOTHING;


-- Jelszó: admin123456.!
-- MD5 hash: 1c548a47ff71343753a806954a6ff336
INSERT INTO app_user (user_id, library_id, role_id, name, date_of_birth, email, password_hash, address) VALUES
    (1, 1, 1, 'Admin Elek', '1980-01-01', 'admin@library.hu', '1c548a47ff71343753a806954a6ff336', 'Admin Address')
ON CONFLICT (user_id) DO NOTHING;
---
INSERT INTO book (book_id, title, author, isbn, publication_year, category) VALUES
-- Eredeti könyvek
(1, 'It', 'Stephen King', '978-0670813025', 1986, 'Horror'),
(2, 'The Hitchhiker''s Guide to the Galaxy', 'Douglas Adams', '978-0345391803', 1979, 'Sci-fi'),
(3, '1984', 'George Orwell', '978-0451524935', 1949, 'Dystopia'),

-- SCI-FI / FANTASY (15 cím)
(4, 'Dune', 'Frank Herbert', '978-0441172719', 1965, 'Sci-fi'),
(5, 'Foundation', 'Isaac Asimov', '978-0553382570', 1951, 'Sci-fi'),
(6, 'The Lord of the Rings', 'J.R.R. Tolkien', '978-0618260214', 1954, 'Fantasy'),
(7, 'Neuromancer', 'William Gibson', '978-0441569562', 1984, 'Sci-fi'),
(8, 'A Wizard of Earthsea', 'Ursula K. Le Guin', '978-0547722742', 1968, 'Fantasy'),
(9, 'Fahrenheit 451', 'Ray Bradbury', '978-1451673319', 1953, 'Dystopia'),
(10, 'Game of Thrones', 'George R.R. Martin', '978-0553103540', 1996, 'Fantasy'),
(11, 'Ender''s Game', 'Orson Scott Card', '978-0812550702', 1985, 'Sci-fi'),
(12, 'The Left Hand of Darkness', 'Ursula K. Le Guin', '978-0441478123', 1969, 'Sci-fi'),
(13, 'The Name of the Wind', 'Patrick Rothfuss', '978-0756404741', 2007, 'Fantasy'),
(14, 'Red Mars', 'Kim Stanley Robinson', '978-0553560731', 1992, 'Sci-fi'),
(15, 'The Martian', 'Andy Weir', '978-0804139021', 2014, 'Sci-fi'),
(16, 'Starship Troopers', 'Robert A. Heinlein', '978-0441783588', 1959, 'Sci-fi'),
(17, 'The Colour of Magic', 'Terry Pratchett', '978-0061020611', 1983, 'Fantasy'),
(18, 'Children of Time', 'Adrian Tchaikovsky', '978-0356504959', 2015, 'Sci-fi'),

-- NOVELLÁK / IRODALMI / KLASSZIKUS (20 cím)
(19, 'The Great Gatsby', 'F. Scott Fitzgerald', '978-0743273565', 1925, 'Literary Fiction'),
(20, 'To Kill a Mockingbird', 'Harper Lee', '978-0446310789', 1960, 'Literary Fiction'),
(21, 'Moby Dick', 'Herman Melville', '978-0142437247', 1851, 'Classic'),
(22, 'Pride and Prejudice', 'Jane Austen', '978-0141439518', 1813, 'Classic'),
(23, 'The Picture of Dorian Gray', 'Oscar Wilde', '978-0141441511', 1890, 'Classic'),
(24, 'Crime and Punishment', 'Fyodor Dostoevsky', '978-0486415871', 1866, 'Classic'),
(25, 'The Catcher in the Rye', 'J.D. Salinger', '978-0316769174', 1951, 'Literary Fiction'),
(26, 'One Hundred Years of Solitude', 'Gabriel García Márquez', '978-0061120090', 1967, 'Literary Fiction'),
(27, 'Slaughterhouse-Five', 'Kurt Vonnegut', '978-0440180296', 1969, 'Literary Fiction'),
(28, 'The Stranger', 'Albert Camus', '978-0679720201', 1942, 'Philosophical'),
(29, 'Mrs. Dalloway', 'Virginia Woolf', '978-0156628709', 1925, 'Literary Fiction'),
(30, 'The Metamorphosis', 'Franz Kafka', '978-0805208693', 1915, 'Novella'),
(31, 'Of Mice and Men', 'John Steinbeck', '978-0140177398', 1937, 'Literary Fiction'),
(32, 'Dubliners', 'James Joyce', '978-0486268712', 1914, 'Short Stories'),
(33, 'The Old Man and the Sea', 'Ernest Hemingway', '978-0684801223', 1952, 'Novella'),
(34, 'Wuthering Heights', 'Emily Brontë', '978-0140434190', 1847, 'Classic'),
(35, 'Jane Eyre', 'Charlotte Brontë', '978-0140434923', 1847, 'Classic'),
(36, 'Frankenstein', 'Mary Shelley', '978-0486282121', 1818, 'Classic'),
(37, 'Dracula', 'Bram Stoker', '978-0486411095', 1897, 'Horror'),
(38, 'Gone Girl', 'Gillian Flynn', '978-0307588371', 2012, 'Thriller'),

-- REGÉNYEK (HORROR/THRILLER/EGYÉB) (15 cím)
(39, 'The Shining', 'Stephen King', '978-0385121675', 1977, 'Horror'),
(40, 'Misery', 'Stephen King', '978-0451153549', 1987, 'Horror'),
(41, 'The Da Vinci Code', 'Dan Brown', '978-0385504201', 2003, 'Thriller'),
(42, 'Girl with the Dragon Tattoo', 'Stieg Larsson', '978-0307455985', 2005, 'Thriller'),
(43, 'Where the Crawdads Sing', 'Delia Owens', '978-0735219090', 2018, 'Literary Fiction'),
(44, 'The Secret History', 'Donna Tartt', '978-0679733355', 1992, 'Literary Fiction'),
(45, 'The Road', 'Cormac McCarthy', '978-0307387897', 2006, 'Dystopia'),
(46, 'Rebecca', 'Daphne du Maurier', '978-0380710111', 1938, 'Gothic'),
(47, 'Circe', 'Madeline Miller', '978-0316556347', 2018, 'Mythology'),
(48, 'Kafka on the Shore', 'Haruki Murakami', '978-1400079278', 2002, 'Magic Realism'),
(49, 'Norwegian Wood', 'Haruki Murakami', '978-0375704024', 1987, 'Literary Fiction'),
(50, 'Project Hail Mary', 'Andy Weir', '978-0593135204', 2021, 'Sci-fi'),
(51, 'The Silent Patient', 'Alex Michaelides', '978-1250301703', 2019, 'Thriller'),
(52, 'The God of Small Things', 'Arundhati Roy', '978-0679745587', 1997, 'Literary Fiction'),
(53, 'Atomic Habits', 'James Clear', '978-0735211292', 2018, 'Self-Help')

ON CONFLICT (book_id) DO NOTHING;

---

INSERT INTO item (item_id, book_id, library_id, item_condition, shelf_mark) VALUES
-- Eredeti és több példányban lévő könyvek (ID 1-29)
(1, 1, 1, 'good', 'SK-101-A'), (2, 1, 1, 'average', 'SK-101-B'), (3, 1, 1, 'new', 'SK-101-C'),
(4, 2, 1, 'good', 'DA-201-A'), (5, 2, 1, 'worn', 'DA-201-B'),
(6, 3, 1, 'good', 'GO-301-A'),
(7, 4, 1, 'good', 'F-004-A'), (8, 4, 1, 'average', 'F-004-B'),
(9, 5, 1, 'new', 'F-005-A'), (10, 5, 1, 'good', 'F-005-B'),
(11, 6, 1, 'good', 'F-006-A'), (12, 6, 1, 'good', 'F-006-B'), (13, 6, 1, 'worn', 'F-006-C'),
(14, 7, 1, 'good', 'SF-007-A'), (15, 8, 1, 'average', 'F-008-A'),
(16, 9, 1, 'new', 'SF-009-A'), (17, 9, 1, 'good', 'SF-009-B'),
(18, 10, 1, 'good', 'F-010-A'), (19, 10, 1, 'good', 'F-010-B'), (20, 10, 1, 'new', 'F-010-C'),
(21, 11, 1, 'good', 'SF-011-A'), (22, 12, 1, 'good', 'SF-012-A'), (23, 13, 1, 'good', 'F-013-A'),
(24, 14, 1, 'average', 'SF-014-A'), (25, 15, 1, 'new', 'SF-015-A'), (26, 15, 1, 'good', 'SF-015-B'),
(27, 16, 1, 'good', 'SF-016-A'), (28, 17, 1, 'good', 'F-017-A'), (29, 18, 1, 'average', 'SF-018-A'),

-- Klasszikusok (ID 30-49)
(30, 19, 1, 'good', 'L-019-A'), (31, 20, 1, 'good', 'L-020-A'), (32, 21, 1, 'average', 'C-021-A'),
(33, 22, 1, 'new', 'C-022-A'), (34, 23, 1, 'good', 'C-023-A'), (35, 24, 1, 'average', 'C-024-A'),
(36, 25, 1, 'good', 'L-025-A'), (37, 26, 1, 'good', 'L-026-A'), (38, 27, 1, 'average', 'L-027-A'),
(39, 28, 1, 'good', 'P-028-A'), (40, 29, 1, 'good', 'L-029-A'), (41, 30, 1, 'new', 'N-030-A'),
(42, 31, 1, 'good', 'L-031-A'), (43, 32, 1, 'average', 'SS-032-A'), (44, 33, 1, 'good', 'N-033-A'),
(45, 34, 1, 'worn', 'C-034-A'), (46, 35, 1, 'good', 'C-035-A'), (47, 36, 1, 'good', 'C-036-A'),
(48, 37, 1, 'good', 'H-037-A'), (49, 38, 1, 'average', 'T-038-A'),

-- Modern regények/Thriller (ID 50-66)
(50, 39, 1, 'good', 'H-039-A'), (51, 39, 1, 'new', 'H-039-B'),
(52, 40, 1, 'good', 'H-040-A'),
(53, 41, 1, 'good', 'T-041-A'),
(54, 42, 1, 'average', 'T-042-A'),
(55, 43, 1, 'good', 'L-043-A'), (56, 43, 1, 'good', 'L-043-B'),
(57, 44, 1, 'good', 'L-044-A'),
(58, 45, 1, 'good', 'D-045-A'),
(59, 46, 1, 'good', 'G-046-A'),
(60, 47, 1, 'new', 'MY-047-A'),
(61, 48, 1, 'good', 'MR-048-A'),
(62, 49, 1, 'good', 'L-049-A'),
(63, 50, 1, 'good', 'SF-050-A'),
(64, 51, 1, 'average', 'T-051-A'),
(65, 52, 1, 'good', 'L-052-A'),
(66, 53, 1, 'new', 'SH-053-A')

ON CONFLICT (item_id) DO NOTHING;