import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { Auth } from './auth';

export type ReservationStatus = 'pending' | 'ready' | 'expired' | 'fulfilled';

export interface Reservation {
  reservation_id: number;
  book_id: number;
  user_id: number;
  queue_number: number;
  reservation_date: string | null;
  expiry_date: string | null;
  status: ReservationStatus;
}

@Injectable({
  providedIn: 'root'
})
export class ReservationService {
  private http = inject(HttpClient);
  private auth = inject(Auth);

  private apiUrl = 'http://localhost:5000/api';

  private requireUserId(): number {
    const u: any = this.auth.getCurrentUser();
    const id = u?.user_id ?? u?.id;
    if (!id) throw new Error('Nincs bejelentkezett felhasználó (user_id hiányzik).');
    return Number(id);
  }

  getMyReservations(status: ReservationStatus | 'all' = 'all'): Observable<Reservation[]> {
    let userId: number;
    try {
      userId = this.requireUserId();
    } catch (e: any) {
      return throwError(() => e);
    }

    return this.http.get<Reservation[]>(`${this.apiUrl}/users/${userId}/reservations`, {
      params: { status }
    });
  }

  createReservation(bookId: number): Observable<any> {
    return this.http.post(`${this.apiUrl}/reservations`, { book_id: bookId });
  }

  cancelReservation(reservationId: number): Observable<any> {
    return this.http.post(`${this.apiUrl}/reservations/${reservationId}/cancel`, {});
  }

  getReservationsForBook(bookId: number): Observable<Reservation[]> {
    return this.http.get<Reservation[]>(`${this.apiUrl}/books/${bookId}/reservations`);
  }

  updateReservationStatus(reservationId: number, status: ReservationStatus): Observable<Reservation> {
    return this.http.post<Reservation>(`${this.apiUrl}/reservations/${reservationId}/status`, { status });
  }
}
