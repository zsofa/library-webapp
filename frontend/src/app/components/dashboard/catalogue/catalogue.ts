import { Component, inject, OnInit } from '@angular/core';
import { CartService } from '../../../services/cart-service';
import { Book } from '../../../models/book.model';
import { BookService } from '../../../services/book-service';
import { Observable, combineLatest, BehaviorSubject, map } from 'rxjs';
import { AsyncPipe, NgClass } from '@angular/common';
import { compileNgModule } from '@angular/compiler';

@Component({
  selector: 'app-catalogue',
  imports: [AsyncPipe, NgClass],
  templateUrl: './catalogue.html',
  styleUrl: './catalogue.css'
})
export class Catalogue implements OnInit {

  cartService = inject(CartService);
  bookService = inject(BookService);

  toBeRequestedBook: Book | null = null;
  books$: Observable<Book[]> | undefined;

  searchText$ = new BehaviorSubject<string>('');
  filteredBooks$: Observable<Book[]> | undefined;

  constructor() { }

  ngOnInit(): void {
    this.filteredBooks$ = combineLatest([
      this.bookService.getBooks(),
      this.searchText$
    ]).pipe(
      map(([books, term]) => {
        if (!term) return books;

        const lowerTerm = term.toLowerCase();
        return books.filter(b =>
          b.title.toLowerCase().includes(lowerTerm) ||
          b.author.toLowerCase().includes(lowerTerm)
        );
      })
    );
  }

  onSearch(event: Event) {
    const input = event.target as HTMLInputElement;
    this.searchText$.next(input.value);
  }

  openRequestModal(book: Book) {
    this.toBeRequestedBook = book;
  }

  confirmRequest() {
    if (!this.toBeRequestedBook) return;

    this.bookService.requestBook(this.toBeRequestedBook.id).subscribe(() => {
      this.cartService.showAlert(`"${this.toBeRequestedBook?.title}" sikeresen előjegyezve`, 'warning');
      this.books$ = this.bookService.getBooks();
      this.toBeRequestedBook = null;
    });
  }

  addToCart(book: Book) {
    this.cartService.addBook(book);
    this.cartService.showAlert(`"${book.title}" hozzáadva a kosárhoz`, 'success');
  }
}