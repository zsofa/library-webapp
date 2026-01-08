import { Component, OnInit, inject } from '@angular/core';
import { AsyncPipe, DatePipe, NgIf, NgFor } from '@angular/common';
import { Observable } from 'rxjs';
import { Loan } from '../../../models/loan.model';
import { LoanService } from '../../../services/loan-service';
import { CartService } from '../../../services/cart-service';

@Component({
  selector: 'app-mybooks',
  standalone: true,
  imports: [DatePipe, AsyncPipe, NgIf, NgFor],
  templateUrl: './mybooks.html',
  styleUrl: './mybooks.css'
})
export class Mybooks implements OnInit {

  private loanService = inject(LoanService);
  private cartService = inject(CartService);

  loans$!: Observable<Loan[]>;
  selectedLoan: Loan | null = null;

  ngOnInit(): void {
    this.loadLoans();
  }

  loadLoans() {
    this.loans$ = this.loanService.getMyLoansDetailed('true');
  }

  openCancelModal(loan: Loan) {
    this.selectedLoan = loan;
  }

  openRenewModal(loan: Loan) {
    this.selectedLoan = loan;
  }

  returnLoan(loanId: number) {
    this.loanService.returnLoan(loanId).subscribe({
      next: () => {
        this.cartService.showAlert('Könyv visszahozva.', 'success');
        this.loadLoans();
      },
      error: err => {
        console.error('[Mybooks] returnLoan hiba:', err);
        this.cartService.showAlert(err?.error?.message || 'Visszahozás sikertelen.', 'danger');
      }
    });
  }

  renewLoan(loan: Loan) {
    this.loanService.extendLoan(loan.loan_id, 30).subscribe({
      next: () => {
        this.cartService.showAlert('Hosszabbítás sikeres (+30 nap).', 'success');
        this.loadLoans();
      },
      error: err => {
        console.error('[Mybooks] extendLoan hiba:', err);
        this.cartService.showAlert(err?.error?.message || 'Hosszabbítás sikertelen.', 'danger');
      }
    });
  }

  isExpired(dueDate: string | null): boolean {
    if (!dueDate) return false;
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const due = new Date(dueDate);
    due.setHours(0, 0, 0, 0);
    return due.getTime() < today.getTime();
  }

  getRemainingDays(dueDate: string | null): number {
    if (!dueDate) return 0;
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const due = new Date(dueDate);
    due.setHours(0, 0, 0, 0);
    const diffMs = due.getTime() - today.getTime();
    return Math.round(diffMs / (1000 * 60 * 60 * 24));
  }
}
