import { Component, inject, OnInit } from '@angular/core';
import { AsyncPipe, DatePipe, NgFor, NgIf, NgClass } from '@angular/common';
import { Observable, combineLatest, map } from 'rxjs';

import { CartService } from '../../../services/cart-service';
import { ReservationService } from '../../../services/reservation-service';
import { BookService } from '../../../services/book-service';
import { LoanService } from '../../../services/loan-service';
import { Book } from '../../../models/book.model';

type ReservationStatus = 'pending' | 'ready' | 'expired' | 'fulfilled';

export interface ReservationVM {
  reservation_id: number;
  book_id: number;
  title: string;
  author: string;
  reservation_date: string;
  expiry_date: string;
  status: ReservationStatus;
  canBorrow: boolean;
}

@Component({
  selector: 'app-requests',
  standalone: true,
  imports: [DatePipe, AsyncPipe, NgIf, NgFor, NgClass],
  templateUrl: './requests.html',
  styleUrl: './requests.css'
})
export class Requests implements OnInit {
  private reservationService = inject(ReservationService);
  private bookService = inject(BookService);
  private loanService = inject(LoanService);

  cartService = inject(CartService);

  reservations$!: Observable<ReservationVM[]>;
  selectedReservation: ReservationVM | null = null;

  ngOnInit(): void {
    this.load();
  }

  load() {
    this.reservations$ = combineLatest([
      this.reservationService.getMyReservations('all'),
      this.bookService.getBooks()
    ]).pipe(
      map(([rows, books]) => {
        const list = rows ?? [];
        return list.map(r => {
          const b = books.find(bb => bb.id === r.book_id);
          const title = b?.title ?? `Book #${r.book_id}`;
          const author = b?.author ?? '';
          const status = (r.status as ReservationStatus);

          return {
            reservation_id: r.reservation_id,
            book_id: r.book_id,
            title,
            author,
            reservation_date: r.reservation_date ?? '',
            expiry_date: r.expiry_date ?? '',
            status,
            canBorrow: status === 'ready'
          } as ReservationVM;
        });
      })
    );
  }

  statusHu(s: ReservationStatus): string {
    switch (s) {
      case 'pending': return 'Függőben';
      case 'ready': return 'Átvehető';
      case 'expired': return 'Lejárt';
      case 'fulfilled': return 'Teljesítve';
    }
  }

  badgeClass(s: ReservationStatus): string {
    switch (s) {
      case 'pending': return 'bg-warning text-dark';
      case 'ready': return 'bg-info text-dark';
      case 'expired': return 'bg-secondary';
      case 'fulfilled': return 'bg-success';
      default: return 'bg-light text-dark';
    }
  }

  borrowFromReady(r: ReservationVM) {
    this.loanService.createLoanForBook(r.book_id, 14).subscribe({
      next: () => {
        this.cartService.showAlert(`Kölcsönzés sikeres: "${r.title}"`, 'success');
        this.load();
      },
      error: (err) => {
        console.error('[Requests] createLoanForBook error', err);
        this.cartService.showAlert(err?.error?.message || 'Nem sikerült kölcsönözni.', 'danger');
      }
    });
  }

  openCancelModal(r: ReservationVM) {
    this.selectedReservation = r;
  }

  confirmCancel() {
    if (!this.selectedReservation) return;

    this.reservationService.cancelReservation(this.selectedReservation.reservation_id).subscribe({
      next: () => {
        this.cartService.showAlert('Előjegyzés lemondva.', 'warning');
        this.selectedReservation = null;
        this.load();
      },
      error: (err) => {
        console.error('[Requests] cancelReservation error', err);
        this.cartService.showAlert(err?.error?.message || 'Nem sikerült lemondani.', 'danger');
      }
    });
  }
}
