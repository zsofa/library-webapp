import { Component, inject, OnInit } from '@angular/core';
import { Router, RouterOutlet, RouterLinkWithHref, RouterModule } from '@angular/router';

@Component({
  selector: 'app-dashboard',
  imports: [RouterModule, RouterOutlet, RouterLinkWithHref],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.css'
})
export class Dashboard implements OnInit {
  loggedUserName: string | null = null;
  router = inject(Router);

  ngOnInit(): void {
    const user = localStorage.getItem("loggedUser");
    if (!user) {
      this.router.navigateByUrl('');
    } else {
      this.loggedUserName = user;
    }
  }

  onLogout() {
    localStorage.removeItem("loggedUser");
    this.router.navigateByUrl('');
  }
}
