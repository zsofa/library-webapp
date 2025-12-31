import { Component, inject } from '@angular/core';
import { Router, RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';
import { NgIf } from '@angular/common';
import { Auth } from '../../services/auth';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive, NgIf],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.css'
})
export class Dashboard {
  private auth = inject(Auth);
  private router = inject(Router);

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
