import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export type ReservationStatus = 'pending' | 'ready' | 'expired' | 'fulfilled';

export interface AdminStats {
  total_users: number;
  active_users: number;
  total_books: number;
  total_items: number;
  active_loans: number;
  overdue_loans: number;
  total_reservations: number;
}

export interface ReservationRow {
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
export class AdminService {
  private apiUrl = 'http://localhost:5000/api';

  constructor(private http: HttpClient) {}

  getStats(): Observable<AdminStats> {
    return this.http.get<AdminStats>(`${this.apiUrl}/admin/stats`);
  }

  getReservationsForBook(bookId: number): Observable<ReservationRow[]> {
    return this.http.get<ReservationRow[]>(`${this.apiUrl}/books/${bookId}/reservations`);
  }

  setReservationStatus(reservationId: number, status: ReservationStatus): Observable<ReservationRow> {
    return this.http.post<ReservationRow>(`${this.apiUrl}/reservations/${reservationId}/status`, { status });
  }

  expireOverdueReservations(): Observable<{ expired_count: number }> {
    return this.http.post<{ expired_count: number }>(`${this.apiUrl}/admin/reservations/expire`, {});
  }
}
