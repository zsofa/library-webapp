import { Component, inject, OnInit } from '@angular/core';
import { Router, RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';
import { NgIf, AsyncPipe } from '@angular/common';
import { map, Observable, of } from 'rxjs';

import { Auth } from '../../services/auth';
import { ReservationService } from '../../services/reservation-service';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive, NgIf, AsyncPipe],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.css'
})
export class Dashboard implements OnInit {
  private auth = inject(Auth);
  private router = inject(Router);
  private reservationService = inject(ReservationService);

  readyCount$: Observable<number> = of(0);

  ngOnInit(): void {
    this.readyCount$ = this.reservationService.getMyReservations('all').pipe(
      map(rows => (rows ?? []).filter(r => !!r.can_borrow).length)
    );
  }

  get userEmail(): string {
    const u: any = this.auth.getCurrentUser();
    return u?.email ?? '';
  }

  get userRole(): string {
    const u: any = this.auth.getCurrentUser();
    return (u?.role ?? '').toLowerCase();
  }

  get isAdmin(): boolean {
    return this.userRole === 'admin';
  }

  logout() {
    this.auth.logout();
    this.router.navigateByUrl('/');
  }
}
