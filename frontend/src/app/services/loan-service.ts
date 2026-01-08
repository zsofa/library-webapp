import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { Loan } from '../models/loan.model';
import { Auth } from './auth';

@Injectable({
  providedIn: 'root'
})
export class LoanService {

  private http = inject(HttpClient);
  private auth = inject(Auth);

  private apiUrl = 'http://localhost:5000/api';

  getMyLoansDetailed(active: 'true' | 'false' | 'all' = 'true'): Observable<Loan[]> {
    const user = this.auth.getCurrentUser();
    if (!user) {
      return throwError(() => new Error('Nincs bejelentkezett felhasználó.'));
    }

    return this.http.get<Loan[]>(`${this.apiUrl}/me/loans/details`, {
      params: { active }
    });
  }

  getMyLoans(active: 'true' | 'false' | 'all' = 'true'): Observable<Loan[]> {
    const user = this.auth.getCurrentUser();
    if (!user) {
      return throwError(() => new Error('No logged in user.'));
    }

    return this.http.get<Loan[]>(`${this.apiUrl}/users/${user.user_id}/loans`, {
      params: { active }
    });
  }

  createLoanForBook(bookId: number, loanDays: number = 14): Observable<Loan> {
    return this.http.post<Loan>(`${this.apiUrl}/loans`, {
      book_id: bookId,
      loan_days: loanDays
    });
  }

  returnLoan(loanId: number): Observable<any> {
    return this.http.post(`${this.apiUrl}/loans/${loanId}/return`, {});
  }

  extendLoan(loanId: number, extraDays: number = 30): Observable<any> {
    return this.http.post(`${this.apiUrl}/loans/${loanId}/extend`, {
      extra_days: extraDays
    });
  }
}
