import { Component, inject, OnInit } from '@angular/core';
import { AsyncPipe, NgClass } from '@angular/common';
import { BehaviorSubject, Observable, combineLatest, map } from 'rxjs';

import { CartService } from '../../../services/cart-service';
import { BookService } from '../../../services/book-service';
import { ReservationService } from '../../../services/reservation-service';
import { LoanService } from '../../../services/loan-service';
import { Book } from '../../../models/book.model';

@Component({
  selector: 'app-catalogue',
  standalone: true,
  imports: [AsyncPipe, NgClass],
  templateUrl: './catalogue.html',
  styleUrl: './catalogue.css'
})
export class Catalogue implements OnInit {
  cartService = inject(CartService);
  bookService = inject(BookService);
  reservationService = inject(ReservationService);
  loanService = inject(LoanService);

  toBeRequestedBook: Book | null = null;

  searchText$ = new BehaviorSubject<string>('');
  filteredBooks$!: Observable<Book[]>;

  ngOnInit(): void {
    this.filteredBooks$ = combineLatest([
      this.bookService.getBooks(),
      this.searchText$
    ]).pipe(
      map(([books, term]) => {
        if (!term) return books;
        const t = term.toLowerCase();
        return books.filter(b =>
          b.title.toLowerCase().includes(t) ||
          b.author.toLowerCase().includes(t)
        );
      })
    );
  }

  onSearch(event: Event) {
    const input = event.target as HTMLInputElement;
    this.searchText$.next(input.value);
  }

  borrow(book: Book) {
    const beforeAvail = (book as any).availableItems ?? null;
    const beforeTotal = (book as any).totalItems ?? null;

    this.loanService.createLoanForBook(book.id, 14).subscribe({
      next: () => {
        const extra =
          beforeAvail !== null && beforeTotal !== null
            ? ` (elérhető: ${beforeAvail} / összes: ${beforeTotal})`
            : '';

        this.cartService.showAlert(`Kölcsönzés sikeres: "${book.title}"${extra}`, 'success');
        this.bookService.getBooks().subscribe();
      },
      error: (err) => {
        console.error('[Catalogue] createLoanForBook error', err);
        const msg = err?.error?.message || 'Nem sikerült kölcsönözni.';
        this.cartService.showAlert(msg, 'danger');
      }
    });
  }

  openRequestModal(book: Book) {
    this.toBeRequestedBook = book;
  }

  confirmRequest() {
    if (!this.toBeRequestedBook) return;

    this.reservationService.createReservation(this.toBeRequestedBook.id).subscribe({
      next: () => {
        this.cartService.showAlert(`Előjegyezve: "${this.toBeRequestedBook?.title}"`, 'warning');
        this.toBeRequestedBook = null;
      },
      error: (err) => {
        console.error('[Catalogue] createReservation error', err);
        const msg = err?.error?.message || 'Nem sikerült előjegyezni.';
        this.cartService.showAlert(msg, 'danger');
      }
    });
  }
}
