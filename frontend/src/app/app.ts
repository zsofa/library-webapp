import { Component, signal } from '@angular/core';
import { RouterOutlet } from '@angular/router';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App {
  protected readonly title = signal('Konyvkolcsonzo');
  loggedUserName: string = '';

  constructor() {
    const loggedData = localStorage.getItem("loggedUser");

    if (loggedData != null) {
      this.loggedUserName = loggedData;
    }
  }
}
