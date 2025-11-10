import { Component, inject } from '@angular/core';
import { CartService } from '../../../services/cart-service';

@Component({
  selector: 'app-catalogue',
  imports: [],
  templateUrl: './catalogue.html',
  styleUrl: './catalogue.css'
})
export class Catalogue {

  cartService = inject(CartService)
  alertMessage = '';
  alertType: 'success' | 'danger' = 'success';

  books = [
    { id: 1, title: 'A Gyűrűk Ura: A Gyűrű Szövetsége', author: 'J.R.R. Tolkien', available: true },
    { id: 2, title: 'A Gyűrűk Ura: A Két Torony', author: 'J.R.R. Tolkien', available: true },
    { id: 3, title: 'A Gyűrűk Ura: A Király visszatér', author: 'J.R.R. Tolkien', available: false },
    { id: 3, title: 'A Hobbit: Váratlan Utazás', author: 'J.R.R. Tolkien', available: true },
    { id: 3, title: 'Harry Potter és a bölcsek köve', author: 'J.K Rowling', available: true },
    { id: 3, title: 'Harry Potter és a Titkok Kamrája', author: 'J.K Rowling', available: false }
  ];

  addToCart(book: any) {
    this.cartService.addBook(book);
    this.showAlert(`"${book.title}" hozzáadva a kosárhoz`, 'success');
  }
  showAlert(message: string, type: 'success' | 'danger') {
    this.alertMessage = message;
    this.alertType = type;
    setTimeout(() => {
      this.alertMessage = '';
    }, 3000);
  }

}
