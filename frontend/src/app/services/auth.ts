import { Injectable } from '@angular/core';
import { Observable, throwError, tap } from 'rxjs';
import { HttpClient } from '@angular/common/http';
import { User } from '../models/user.model';

interface LoginResponse {
  access_token: string;
  refresh_token: string;
  user: any;
}

@Injectable({
  providedIn: 'root'
})
export class Auth {
  private apiUrl = 'http://localhost:5000/api';

  constructor(private http: HttpClient) {}

  login(email: string, password: string): Observable<LoginResponse> {
    return this.http.post<LoginResponse>(`${this.apiUrl}/login`, { email, password }).pipe(
      tap(res => {
        const u = res.user || {};
        const normalized: User = {
          user_id: u.user_id ?? u.id,
          name: u.name ?? '',
          email: u.email ?? '',
          role: u.role,
          library_id: u.library_id 
        };

        localStorage.setItem('access_token', res.access_token);
        localStorage.setItem('refresh_token', res.refresh_token);
        localStorage.setItem('user', JSON.stringify(normalized));
      })
    );
  }

  logout(): void {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
  }

  getCurrentUser(): User | null {
    const raw = localStorage.getItem('user');
    if (!raw) return null;
    try {
      return JSON.parse(raw);
    } catch {
      return null;
    }
  }

  isLoggedIn(): boolean {
    return !!localStorage.getItem('access_token');
  }

  getAccessToken(): string | null {
    return localStorage.getItem('access_token');
  }

  isAdmin(): boolean {
    const user = this.getCurrentUser();
    const role = (user?.role || '').toLowerCase();
    return role === 'admin';
  }

  getRole(): string | null {
    return this.getCurrentUser()?.role ?? null;
  }
}
