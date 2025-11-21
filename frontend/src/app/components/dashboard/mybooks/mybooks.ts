import { Component, inject, OnInit } from '@angular/core';
import { AsyncPipe, DatePipe } from '@angular/common';
import { BookService } from '../../../services/book-service';
import { Observable } from 'rxjs';
import { Book } from '../../../models/book.model';

@Component({
  selector: 'app-mybooks',
  imports: [DatePipe, AsyncPipe],
  templateUrl: './mybooks.html',
  styleUrl: './mybooks.css'
})
export class Mybooks implements OnInit {

  bookService = inject(BookService);
  borrowedBooks$: Observable<Book[]> | undefined;
  selectedBook: Book | null = null;

  ngOnInit(): void {
    this.loadBorrowedBooks();
  }

  loadBorrowedBooks() {
    this.borrowedBooks$ = this.bookService.getMyBooks();
  }

  openCancelModal(book: Book) {
    this.selectedBook = book;
  }

  openRenewModal(book: Book) {
    this.selectedBook = book;
  }

  returnBook(bookId: number) {
    this.bookService.returnBook(bookId).subscribe(() => {
      this.loadBorrowedBooks();
    });
  }

  renewBook(book: Book) {
    if (!book.extended) {
      this.bookService.renewBook(book.id).subscribe(() => {
        this.loadBorrowedBooks();
      });
    }
  }

  isExpired(expirationDate: Date): boolean {
    return new Date(expirationDate) < new Date();
  }

  getRemainingDays(expirationDate: Date | null | undefined): number {
    if (!expirationDate) return 0;
    const now = new Date();
    now.setHours(0, 0, 0, 0);
    const exp = new Date(expirationDate);
    exp.setHours(0, 0, 0, 0);
    const diff = exp.getTime() - now.getTime();
    return Math.round(diff / (1000 * 60 * 60 * 24));
  }

  isExtended(book: Book) {
    return book.extended;
  }
}
