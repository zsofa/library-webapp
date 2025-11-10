import { Component, inject, OnInit } from '@angular/core';
import { MyBooksService } from '../../../services/my-books-service';
import { DatePipe } from '@angular/common';

@Component({
  selector: 'app-mybooks',
  imports: [DatePipe],
  templateUrl: './mybooks.html',
  styleUrl: './mybooks.css'
})
export class Mybooks implements OnInit {

  myBooksService = inject(MyBooksService);
  myBooks: any[] = [];

  ngOnInit(): void {
    this.myBooks = this.myBooksService.getBooks();
  }

  isExpired(expirationDate: string): boolean {
    return new Date(expirationDate) < new Date();
  }

  removeFromMyBooks(index: number) {
    this.myBooksService.removeBook(index);
  }

}
