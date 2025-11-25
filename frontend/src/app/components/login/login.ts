import { ParseSourceFile } from '@angular/compiler';
import { Component, inject } from '@angular/core';
import { FormBuilder, FormGroup, FormsModule, Validators } from '@angular/forms';
import { RouterOutlet, RouterLink, Router } from '@angular/router';

@Component({
  selector: 'app-login',
  imports: [FormsModule, RouterOutlet, RouterLink],
  templateUrl: './login.html',
  styleUrl: './login.css'
})
export class Login {
  loginObj: any = {
    email: '',
    password: ''
  };
  router = inject(Router);

  onLogin() {
    if (this.loginObj.email == 'user' && this.loginObj.password == 'user') {
      this.router.navigateByUrl('/dashboard/mybooks');
      localStorage.setItem('loggedUser', 'user');
    } else {
      alert("Hibás email cím/jelszó!");
    }
  }
}
