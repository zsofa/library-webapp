import { Component, inject, OnInit } from '@angular/core';
import { AsyncPipe, NgFor, NgIf, DatePipe, NgClass } from '@angular/common';
import { FormsModule } from '@angular/forms';

import { BookService } from '../../../services/book-service';
import { AdminService, AdminItemRow } from '../../../services/admin-service';
import { CartService } from '../../../services/cart-service';
import { Book } from '../../../models/book.model';

type ItemCondition = 'new' | 'good' | 'used' | 'damaged';

@Component({
  selector: 'app-admin',
  standalone: true,
  imports: [NgIf, NgFor, AsyncPipe, DatePipe, FormsModule, NgClass],
  templateUrl: './admin.html',
  styleUrl: './admin.css'
})
export class Admin implements OnInit {
  private bookService = inject(BookService);
  private adminService = inject(AdminService);
  private cartService = inject(CartService);

  loading = false;
  errorMsg = '';
  successMsg = '';

  books: Book[] = [];

  selectedBook: Book | null = null;
  items: AdminItemRow[] = [];

  addCount = 1;
  addCondition: ItemCondition = 'new';
  shelfMarkPrefix = 'AUTO';

  ngOnInit(): void {
    this.reloadBooks();
  }

  reloadBooks() {
    this.errorMsg = '';
    this.successMsg = '';
    this.loading = true;

    this.bookService.getBooks().subscribe({
      next: (books) => {
        this.books = books ?? [];
        this.loading = false;
      },
      error: (err) => {
        console.error('[Admin] getBooks error', err);
        this.errorMsg = 'Nem sikerült betölteni a könyvlistát.';
        this.loading = false;
      }
    });
  }

  openBook(b: Book) {
    this.selectedBook = b;
    this.loadItems(b.id);
  }

  loadItems(bookId: number) {
    this.errorMsg = '';
    this.successMsg = '';
    this.loading = true;

    this.adminService.listItemsForBook(bookId, false).subscribe({
      next: (rows) => {
        this.items = rows ?? [];
        this.loading = false;
      },
      error: (err) => {
        console.error('[Admin] listItemsForBook error', err);
        this.errorMsg = err?.error?.message || 'Nem sikerült lekérni a példányokat.';
        this.loading = false;
      }
    });
  }

  addItems() {
    if (!this.selectedBook) return;

    this.errorMsg = '';
    this.successMsg = '';
    this.loading = true;

    this.adminService.addItemsForBook(this.selectedBook.id, this.addCount, this.addCondition, this.shelfMarkPrefix).subscribe({
      next: () => {
        this.cartService.showAlert('Példány(ok) hozzáadva.', 'success');
        this.successMsg = 'Példány(ok) hozzáadva.';
        this.loading = false;
        this.reloadBooks();
        this.loadItems(this.selectedBook!.id);
      },
      error: (err) => {
        console.error('[Admin] addItems error', err);
        this.errorMsg = err?.error?.message || 'Nem sikerült hozzáadni a példány(oka)t.';
        this.loading = false;
      }
    });
  }

  removeOne() {
    if (!this.selectedBook) return;

    this.errorMsg = '';
    this.successMsg = '';
    this.loading = true;

    this.adminService.removeOneAvailableItem(this.selectedBook.id).subscribe({
      next: () => {
        this.cartService.showAlert('Egy elérhető példány eltávolítva.', 'warning');
        this.successMsg = 'Egy elérhető példány eltávolítva.';
        this.loading = false;
        this.reloadBooks();
        this.loadItems(this.selectedBook!.id);
      },
      error: (err) => {
        console.error('[Admin] removeOne error', err);
        this.errorMsg = err?.error?.message || 'Nem sikerült eltávolítani (lehet nincs szabad példány).';
        this.loading = false;
      }
    });
  }

  itemBadgeClass(isLoaned: boolean): string {
    return isLoaned ? 'bg-secondary' : 'bg-success';
  }

  itemBadgeText(isLoaned: boolean): string {
    return isLoaned ? 'Kint van' : 'Elérhető';
  }
}
