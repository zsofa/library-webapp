import { Component, inject, OnInit } from '@angular/core';
import { Router, RouterOutlet, RouterLinkWithHref, RouterModule } from '@angular/router';
import { CartService } from '../../services/cart-service';
import { BookService } from '../../services/book-service';
import { forkJoin } from 'rxjs';
import { Book } from '../../models/book.model';
import { Catalogue } from './catalogue/catalogue';

@Component({
  selector: 'app-dashboard',
  imports: [RouterModule, RouterOutlet, RouterLinkWithHref],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.css'
})
export class Dashboard implements OnInit {
  loggedUserName: string | null = null;
  router = inject(Router);
  cartService = inject(CartService);
  bookService = inject(BookService);

  ngOnInit(): void {
    const user = localStorage.getItem("loggedUser");
    if (!user) {
      this.router.navigateByUrl('');
    } else {
      this.loggedUserName = user;
    }
  }

  get cartBooks() {
    return this.cartService.getBooks();
  }
  removeFromCart(index: number) {
    this.cartService.removeBook(index);
  }
  emptyCart() {
    this.cartService.clearCart();
  }

  borrowBooks() {
    const booksToBorrow = this.cartService.getBooks();
    if (booksToBorrow.length === 0) return;

    const borrowObservables = booksToBorrow.map(book => {
      return this.bookService.borrowBook(book.id);
    })

    forkJoin(borrowObservables).subscribe({
      next: () => {
        this.cartService.clearCart();
        this.cartService.showAlert('Sikeres kölcsönzés! Jó olvasást!', 'success');
      },
      error: (err) => {
        console.error('Borrowing failed:', err);
        this.cartService.showAlert('Hiba történt a kölcsönzés során.', 'danger');
      }
    });
  }

  onLogout() {
    localStorage.removeItem("loggedUser");
    localStorage.removeItem('library_cart');
    this.router.navigateByUrl('');
  }
}
