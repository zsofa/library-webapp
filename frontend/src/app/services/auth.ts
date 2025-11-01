import { Injectable } from '@angular/core';
import { User } from '../models/user.model';
import { Observable, of, throwError } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class Auth {
  private currentUser: User | null = null;

  constructor() { }

  login(email: string, password: string): Observable<User> {
    if (email === "user@user.com" && password === "1234") {
      const user: User = {
        id: 1,
        name: 'User',
        email,
      };
      localStorage.setItem('user', JSON.stringify(user));
      this.currentUser = user;
      return of(user);
    } else {
      return throwError(() => new Error('Invalid credentials'));
    }
  }

  logout(): void {
    localStorage.removeItem('user');
    this.currentUser = null;
  }
  getCurrentUser(): User | null {
    const user = localStorage.getItem('user');
    return user ? JSON.parse(user) : null;
  }

  isLoggedIn(): boolean {
    return !!this.getCurrentUser();
  }
}
