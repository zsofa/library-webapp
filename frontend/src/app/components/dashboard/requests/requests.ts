import { Component, inject, OnInit } from '@angular/core';
import { AsyncPipe, DatePipe } from '@angular/common';
import { CartService } from '../../../services/cart-service';
import { BookService } from '../../../services/book-service';
import { Book } from '../../../models/book.model';
import { Observable } from 'rxjs';

@Component({
  selector: 'app-requests',
  imports: [DatePipe, AsyncPipe],
  templateUrl: './requests.html',
  styleUrl: './requests.css'
})
export class Requests implements OnInit {

  cartService = inject(CartService);
  bookService = inject(BookService);
  requestedBooks$: Observable<Book[]> | undefined;
  selectedRequest: Book | null = null;


  ngOnInit(): void {
    this.loadRequests();
  }

  loadRequests() {
    this.requestedBooks$ = this.bookService.getRequestedBook();
  }
  openCancelModal(book: Book) {
    this.selectedRequest = book;
  }
  confirmCancel() {
    if (!this.selectedRequest) {
      return;
    }
    this.bookService.cancelRequested(this.selectedRequest.id).subscribe(() => {
      this.loadRequests();
      this.selectedRequest = null;
    })
  }

  addToCart(book: Book) {
    this.cartService.addBook(book);
    this.cartService.showAlert(`"${book.title}" hozzáadva a kosárhoz`, 'success');
  }





  // ----------------------------------------------------------------------------------------------------------------

}
