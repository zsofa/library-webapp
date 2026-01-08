import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable, map, of } from 'rxjs';
import { Book, ApiBook } from '../models/book.model';

@Injectable({
  providedIn: 'root'
})
export class BookService {
  private apiUrl = 'http://localhost:5000/api';

  private booksSubject = new BehaviorSubject<Book[]>([]);
  books$ = this.booksSubject.asObservable();

  constructor(private http: HttpClient) {}

  getBooks(): Observable<Book[]> {
    return this.http.get<ApiBook[]>(`${this.apiUrl}/books`).pipe(
      map(apiBooks => apiBooks.map(b => this.mapApiBookToBook(b))),
      map(books => {
        this.booksSubject.next(books);
        return books;
      })
    );
  }

  private mapApiBookToBook(api: ApiBook): Book {
    const total = Number(api.total_items ?? 0);
    const avail = Number(api.available_items ?? 0);
    const wait = Number(api.waitlist_count ?? 0);

    return {
      id: api.book_id,
      title: api.title,
      author: api.author,

      total_items: total,
      availableItems: avail,
      waitlistCount: wait,

      available: avail > 0,

      extended: false,
      requested: false,
      borrowed: false,
      requestedAt: null,
      borrowedDate: null,
      expirationDate: null
    };
  }

  requestBook(bookId: number): Observable<any> {
    return this.http.post(`${this.apiUrl}/reservations`, {
      book_id: bookId
    });
  }

  getMyBooks(): Observable<Book[]> {
    return this.books$.pipe(map(books => books.filter(b => b.borrowed)));
  }

  returnBook(bookId: number): Observable<void> {
    return of(void 0);
  }

  renewBook(bookId: number): Observable<void> {
    return of(void 0);
  }

  getRequestedBook(): Observable<Book[]> {
    return this.books$.pipe(map(books => books.filter(b => b.requested)));
  }

  cancelRequested(bookId: number): Observable<void> {
    return of(void 0);
  }
}
