import { Injectable } from '@angular/core';
import { Book } from '../models/book.model';

@Injectable({
  providedIn: 'root'
})
export class ReqestService {
  private storageKey = 'library_requests';
  requestedBooks: Book[] = [];

  constructor() {
    const savedRequests = localStorage.getItem('library_requests');
    this.requestedBooks = savedRequests ? JSON.parse(savedRequests) : [];
  }

  getRequests() {
    return this.requestedBooks;
  }

  addRequest(book: Book) {
    const requests = this.getRequests();

    if (!requests.find((b: Book) => b.title === book.title)) {
      requests.push(book);
      localStorage.setItem(this.storageKey, JSON.stringify(requests));
    }
  }

  removeRequest(index: number) {
    this.requestedBooks.splice(index, 1);
    this.saveList();
  }

  clearList() {
    this.requestedBooks = [];
    this.saveList();
  }

  private saveList() {
    localStorage.setItem(this.storageKey, JSON.stringify(this.requestedBooks));
  }
}
