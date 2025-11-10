import { Injectable } from '@angular/core';

@Injectable({
  providedIn: 'root'
})
export class MyBooksService {
  private storageKey = 'library_mybooks';
  myBooks: any[] = [];

  constructor() {
    const savedBooks = localStorage.getItem(this.storageKey);
    this.myBooks = savedBooks ? JSON.parse(savedBooks) : [];
  }

  private saveBooks() {
    localStorage.setItem(this.storageKey, JSON.stringify(this.myBooks));
  }

  addBook(book: any) {
    this.myBooks.push(book);
    this.saveBooks();
  }

  addBooks(books: any[]) {
    const borrowedDate = new Date();
    const expirationDate = new Date(borrowedDate);
    expirationDate.setDate(borrowedDate.getDate() + 30);

    const borrowedBooks = books.map(book => ({
      ...book,
      borrowedDate: borrowedDate.toISOString(),
      expirationDate: expirationDate.toISOString()
    }));

    this.myBooks.push(...borrowedBooks);
    this.saveBooks();
  }

  getBooks() {
    return this.myBooks;
  }

  removeBook(index: number) {
    this.myBooks.splice(index, 1);
    this.saveBooks();
  }

  clearBooks() {
    this.myBooks = [];
    this.saveBooks();
  }
}
