import { Component, inject, OnInit } from '@angular/core';
import { AsyncPipe, DatePipe, NgFor, NgIf, NgClass } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { forkJoin, map, Observable, of } from 'rxjs';

import { ReservationService } from '../../../services/reservation-service';
import { BookService } from '../../../services/book-service';
import { Book } from '../../../models/book.model';
import { CartService } from '../../../services/cart-service';

type ReservationStatus = 'pending' | 'ready' | 'expired' | 'fulfilled';

type BookTaskRow = {
  bookId: number;
  title: string;
  author: string;
  waitingCount: number;
  nextStatus: ReservationStatus | null;
  nextReservationId: number | null;
};

type ReservationRow = {
  reservation_id: number;
  book_id: number;
  user_id: number;
  queue_number: number;
  reservation_date: string | null;
  expiry_date: string | null;
  status: ReservationStatus;
};

@Component({
  selector: 'app-admin',
  standalone: true,
  imports: [NgIf, NgFor, AsyncPipe, DatePipe, FormsModule, NgClass],
  templateUrl: './admin.html',
  styleUrl: './admin.css'
})
export class Admin implements OnInit {
  private reservationService = inject(ReservationService);
  private bookService = inject(BookService);
  private cartService = inject(CartService);

  loading = false;
  errorMsg = '';
  successMsg = '';

  tasks: BookTaskRow[] = [];

  selectedBook: Book | null = null;
  waitlist: ReservationRow[] = [];

  waitingOnly = true;

  ngOnInit(): void {
    this.reloadTasks();
  }

  reloadTasks() {
    this.errorMsg = '';
    this.successMsg = '';
    this.loading = true;

    this.bookService.getBooks().subscribe({
      next: (books: Book[]) => {
        if (!books?.length) {
          this.tasks = [];
          this.loading = false;
          return;
        }
        const calls = books.map(b =>
          this.reservationService.getReservationsForBook(b.id).pipe(
            map((rows: ReservationRow[]) => ({ book: b, rows: rows ?? [] }))
          )
        );

        forkJoin(calls).subscribe({
          next: (results) => {
            const rows: BookTaskRow[] = results.map(({ book, rows }) => {
              const waiting = rows.filter(r => r.status === 'pending' || r.status === 'ready');
              const next = waiting[0] ?? null;
              return {
                bookId: book.id,
                title: book.title,
                author: book.author,
                waitingCount: waiting.length,
                nextStatus: next?.status ?? null,
                nextReservationId: next?.reservation_id ?? null
              };
            });

            const filtered = rows
              .filter(r => !this.waitingOnly || r.waitingCount > 0)
              .sort((a, b) => b.waitingCount - a.waitingCount);

            this.tasks = filtered;
            this.loading = false;
          },
          error: (err) => {
            console.error('[Admin] forkJoin waitlists error', err);
            this.errorMsg = err?.error?.message || 'Nem sikerült betölteni a feladatlistát. (Admin token?)';
            this.loading = false;
          }
        });
      },
      error: (err) => {
        console.error('[Admin] getBooks error', err);
        this.errorMsg = 'Nem sikerült lekérni a könyveket.';
        this.loading = false;
      }
    });
  }

  toggleWaitingOnly() {
    this.waitingOnly = !this.waitingOnly;
    this.reloadTasks();
  }

  openDetails(task: BookTaskRow) {
    this.errorMsg = '';
    this.successMsg = '';
    this.loading = true;

    this.bookService.getBooks().subscribe({
      next: (books) => {
        this.selectedBook = books.find(b => b.id === task.bookId) ?? null;

        this.reservationService.getReservationsForBook(task.bookId).subscribe({
          next: (rows: ReservationRow[]) => {
            const all = rows ?? [];
            this.waitlist = this.waitingOnly
              ? all.filter(r => r.status === 'pending' || r.status === 'ready')
              : all;

            this.loading = false;
          },
          error: (err) => {
            console.error('[Admin] getReservationsForBook error', err);
            this.errorMsg = err?.error?.message || 'Nem sikerült lekérni a várólistát.';
            this.loading = false;
          }
        });
      },
      error: () => {
        this.selectedBook = null;
        this.loading = false;
      }
    });
  }

  markNextReady(task: BookTaskRow) {
    this.errorMsg = '';
    this.successMsg = '';

    if (!task.nextReservationId) {
      this.errorMsg = 'Nincs függő/átvehető előjegyzés ehhez a könyvhöz.';
      return;
    }

    if (task.nextStatus === 'ready') {
      this.successMsg = 'A következő előjegyzés már átvehető.';
      return;
    }

    this.loading = true;
    this.reservationService.updateReservationStatus(task.nextReservationId, 'ready').subscribe({
      next: () => {
        this.loading = false;
        this.successMsg = `Átvehetővé téve: ${task.title}`;
        this.cartService.showAlert('A következő előjegyzés átvehető (ready).', 'success');

        const keepSelectedId = this.selectedBook?.id ?? null;
        this.reloadTasks();
        if (keepSelectedId === task.bookId) {
          this.openDetails(task);
        }
      },
      error: (err) => {
        console.error('[Admin] updateReservationStatus error', err);
        this.errorMsg = err?.error?.message || 'Nem sikerült átállítani átvehetőre.';
        this.loading = false;
      }
    });
  }

  statusHu(s: ReservationStatus | null | undefined): string {
    switch (s) {
      case 'pending': return 'Függőben';
      case 'ready': return 'Átvehető';
      case 'expired': return 'Lejárt';
      case 'fulfilled': return 'Teljesítve';
      default: return '—';
    }
  }

  badgeClass(s: ReservationStatus | null | undefined): string {
    switch (s) {
      case 'pending': return 'bg-warning text-dark';
      case 'ready': return 'bg-info text-dark';
      case 'expired': return 'bg-secondary';
      case 'fulfilled': return 'bg-success';
      default: return 'bg-light text-dark';
    }
  }
}
