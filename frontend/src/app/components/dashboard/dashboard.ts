import { Component, inject, OnInit } from '@angular/core';
import { Router, RouterOutlet, RouterLinkWithHref, RouterModule } from '@angular/router';
import { CartService } from '../../services/cart-service';
import { MyBooksService } from '../../services/my-books-service';

@Component({
  selector: 'app-dashboard',
  imports: [RouterModule, RouterOutlet, RouterLinkWithHref],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.css'
})
export class Dashboard implements OnInit {
  loggedUserName: string | null = null;
  router = inject(Router);
  cartService = inject(CartService)
  myBooksService = inject(MyBooksService)

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

    this.myBooksService.addBooks(booksToBorrow);
    this.cartService.clearCart();
  }

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
    localStorage.removeItem('library_cart');
    this.router.navigateByUrl('');
  }
}
