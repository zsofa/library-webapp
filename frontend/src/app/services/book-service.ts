import { Injectable } from '@angular/core';
import { Book } from '../models/book.model';
import { BehaviorSubject, Observable, of } from 'rxjs';
import { observeNotification } from 'rxjs/internal/Notification';

@Injectable({
  providedIn: 'root'
})
export class BookService {
  private storageKey = 'library_books';

  private booksSubject = new BehaviorSubject<Book[]>([]);
  books$ = this.booksSubject.asObservable();

  private bookList: Book[] = [
    { id: 1, title: 'A Gyűrűk Ura: A Gyűrű Szövetsége', author: 'J.R.R. Tolkien', available: true, extended: false, requested: false, borrowed: false },
    { id: 2, title: 'A Gyűrűk Ura: A Két Torony', author: 'J.R.R. Tolkien', available: true, extended: false, requested: false, borrowed: false },
    { id: 3, title: 'A Gyűrűk Ura: A Király visszatér', author: 'J.R.R. Tolkien', available: true, extended: false, requested: false, borrowed: false },
    { id: 4, title: 'A Hobbit: Váratlan Utazás', author: 'J.R.R. Tolkien', available: true, extended: false, requested: false, borrowed: false },
    { id: 5, title: 'Harry Potter és a Bölcsek Köve', author: 'J.K Rowling', available: false, extended: false, requested: false, borrowed: false },
    { id: 6, title: 'Harry Potter és a Titkok Kamrája', author: 'J.K Rowling', available: false, extended: false, requested: false, borrowed: false }
  ];

  constructor() {
    this.initialStorage();
    this.refreshBooks();
  }

  private refreshBooks() {
    const books = this.getBooksFromStorage();
    this.booksSubject.next(books);
  }

  private initialStorage() {
    if (!localStorage.getItem(this.storageKey)) {
      this.saveToLocalStorage(this.bookList);
    }
  }
  private saveToLocalStorage(books: Book[]) {
    localStorage.setItem(this.storageKey, JSON.stringify(books));
  }

  private getBooksFromStorage(): Book[] {
    const data = localStorage.getItem(this.storageKey);
    const books: any[] = data ? JSON.parse(data) : [];

    return books.map(b => {
      if (b.requestedAt) { b.requestedAt = new Date(b.requestedAt); }
      return b;
    });
  }

  //For Catalogue
  getBooks(): Observable<Book[]> {
    this.refreshBooks();
    return this.books$;
  }

  //For Requested Books
  getRequestedBook(): Observable<Book[]> {
    const books = this.getBooksFromStorage();
    const requestedBooks = books.filter(b => b.requested === true);
    return of(requestedBooks);
  }

  requestBook(bookId: number): Observable<void> {
    const books = this.getBooksFromStorage();
    const index = books.findIndex(b => b.id === bookId);

    if (index !== -1) {
      books[index].requested = true;
      books[index].available = false;
      books[index].requestedAt = new Date();
      this.saveToLocalStorage(books);
      this.refreshBooks();
    }
    return of(undefined);
  }

  cancelRequested(bookId: number): Observable<void> {
    const books = this.getBooksFromStorage();
    const index = books.findIndex(b => b.id === bookId);

    if (index !== -1) {
      books[index].requested = false;
      books[index].requestedAt = null;
      this.saveToLocalStorage(books);
    }
    return of(undefined);
  }

  //For Borrowed Books
  getMyBooks(): Observable<Book[]> {
    const books = this.getBooksFromStorage();
    const myBooks = books.filter(b => b.borrowed === true);
    return of(myBooks);
  }

  borrowBook(bookId: number): Observable<void> {
    const books = this.getBooksFromStorage();
    const index = books.findIndex(b => b.id === bookId);

    if (index !== -1) {
      const today = new Date();
      const expiration = new Date(today);
      expiration.setDate(today.getDate() + 30);

      books[index].requested = false;
      books[index].borrowed = true;
      books[index].available = false;
      books[index].borrowedDate = today;
      books[index].expirationDate = expiration;

      this.saveToLocalStorage(books);
      this.refreshBooks();
    }
    return of(undefined);
  }

  renewBook(bookId: number): Observable<void> {
    const books = this.getBooksFromStorage();
    const index = books.findIndex(b => b.id === bookId);

    if (index !== -1 && !books[index].extended) {
      books[index].extended = true;

      const currentExpiration = new Date(books[index].expirationDate || new Date());
      books[index].expirationDate = new Date(currentExpiration.setDate(currentExpiration.getDate() + 30));
      //books[index].expirationDate = newExpiration.toISOString();

      this.saveToLocalStorage(books);
      this.refreshBooks();
    }
    return of(undefined);
  }

  returnBook(bookId: number): Observable<void> {
    const books = this.getBooksFromStorage();
    const index = books.findIndex(b => b.id === bookId);

    if (index !== -1) {
      books[index].borrowed = false;
      books[index].available = true;
      if (books[index].extended) {
        books[index].extended = false;
      }
      this.saveToLocalStorage(books);
      this.refreshBooks();
    }
    return of(undefined);
  }
}
