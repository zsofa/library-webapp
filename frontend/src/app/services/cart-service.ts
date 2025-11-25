import { Injectable } from '@angular/core';

@Injectable({
  providedIn: 'root'
})
export class CartService {
  private storageKey = 'library_cart';
  cartBooks: any[] = [];

  alertMessage = '';
  alertType: 'success' | 'danger' | 'warning' = 'success';

  constructor() {
    const savedCart = localStorage.getItem(this.storageKey);
    this.cartBooks = savedCart ? JSON.parse(savedCart) : [];
  }

  private saveCart() {
    localStorage.setItem(this.storageKey, JSON.stringify(this.cartBooks));
  }

  addBook(book: any) {
    this.cartBooks.push(book);
    this.saveCart();
  }

  removeBook(index: number) {
    this.cartBooks.splice(index, 1);
    this.saveCart();
  }

  clearCart() {
    this.cartBooks = [];
    this.saveCart();
  }

  getBooks() {
    return this.cartBooks;
  }

  showAlert(message: string, type: 'success' | 'danger' | 'warning') {
    this.alertMessage = message;
    this.alertType = type;
    setTimeout(() => {
      this.alertMessage = '';
    }, 3000);
  }
}
