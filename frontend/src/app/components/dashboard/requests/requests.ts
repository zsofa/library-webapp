import { Component, inject, OnInit } from '@angular/core';
import { AsyncPipe, DatePipe, NgFor, NgIf, NgClass } from '@angular/common';
import { Observable, map } from 'rxjs';

import { CartService } from '../../../services/cart-service';
import { ReservationService, ReservationStatus, Reservation } from '../../../services/reservation-service';

export interface ReservationVM {
  reservation_id: number;
  book_id: number;
  title: string;
  author: string;
  reservation_date: string;
  expiry_date: string;
  status: ReservationStatus;
  waiting_ahead: number;
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
  cartService = inject(CartService);

  reservations$!: Observable<ReservationVM[]>;
  selectedReservation: ReservationVM | null = null;

  ngOnInit(): void {
    this.load();
  }

  load() {
    this.reservations$ = this.reservationService.getMyReservations('all').pipe(
      map((rows: Reservation[]) => (rows ?? []).map(r => ({
        reservation_id: r.reservation_id,
        book_id: r.book_id,
        title: r.title ?? `Book #${r.book_id}`,
        author: r.author ?? '',
        reservation_date: r.reservation_date ?? '',
        expiry_date: r.expiry_date ?? '',
        status: r.status,
        waiting_ahead: Number(r.waiting_ahead ?? 0),
        canBorrow: !!r.can_borrow
      })))
    );
  }

  statusHu(s: ReservationStatus): string {
    switch (s) {
      case 'pending': return 'Függőben';
      case 'ready': return 'Aktív';
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

  borrowFromReservation(r: ReservationVM) {
    this.reservationService.borrowFromReservation(r.reservation_id, 14).subscribe({
      next: () => {
        this.cartService.showAlert(`Kölcsönzés sikeres: "${r.title}"`, 'success');
        this.load();
      },
      error: (err) => {
        console.error('[Requests] borrowFromReservation error', err);
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
