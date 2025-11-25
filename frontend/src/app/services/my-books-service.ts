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

  getBook(index: number) {
    return this.myBooks[index];
  }

  removeBook(index: number) {
    this.myBooks.splice(index, 1);
    this.saveBooks();
  }

  clearBooks() {
    this.myBooks = [];
    this.saveBooks();
  }

  renewDate(book: any) {
    // Convert expirationDate string to Date
    const currentExp = new Date(book.expirationDate);

    // Extend by 30 days
    currentExp.setDate(currentExp.getDate() + 30);

    // Save new expiration date (as ISO string for consistency)
    book.expirationDate = currentExp.toISOString();
    book.extended = true;
    // Update localStorage if you’re persisting data
    const books = JSON.parse(localStorage.getItem('library_mybooks') || '[]');
    const index = books.findIndex((b: any) => b.title === book.title);
    if (index !== -1) {
      books[index].expirationDate = book.expirationDate;
      books[index].extended = true;
      localStorage.setItem('library_mybooks', JSON.stringify(books));
    }
  }
}
