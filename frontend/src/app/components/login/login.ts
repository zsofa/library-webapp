import { Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink, RouterOutlet } from '@angular/router';
import { Auth } from '../../services/auth';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [FormsModule, RouterOutlet, RouterLink],
  templateUrl: './login.html',
  styleUrl: './login.css'
})
export class Login {

  private auth = inject(Auth);
  private router = inject(Router);

  loginObj = {
    email: '',
    password: ''
  };

  loading = false;
  errorMessage = '';

  onLogin() {
    this.errorMessage = '';
    this.loading = true;

    this.auth.login(this.loginObj.email, this.loginObj.password).subscribe({
      next: res => {
        const role = res.user?.role ?? 'member';

        this.router.navigateByUrl('/dashboard/home');
      },
      error: err => {
        console.error('[LOGIN ERROR]', err);
        this.errorMessage = err?.error?.message || 'Hibás email vagy jelszó';
        this.loading = false;
      }
    });
  }
}
