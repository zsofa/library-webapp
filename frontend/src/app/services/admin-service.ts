import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface AdminItemRow {
  item_id: number;
  book_id: number;
  library_id: number;
  item_condition: string;
  shelf_mark: string;
  is_loaned: boolean;
}

@Injectable({
  providedIn: 'root'
})
export class AdminService {
  private http = inject(HttpClient);
  private apiUrl = 'http://localhost:5000/api';

  listItemsForBook(bookId: number, availableOnly: boolean = false): Observable<AdminItemRow[]> {
    return this.http.get<AdminItemRow[]>(`${this.apiUrl}/admin/books/${bookId}/items`, {
      params: { available_only: String(availableOnly) }
    });
  }

  addItemsForBook(bookId: number, count: number, itemCondition: 'new'|'good'|'used'|'damaged' = 'new', shelfMarkPrefix: string = 'AUTO'): Observable<any> {
    return this.http.post(`${this.apiUrl}/admin/books/${bookId}/items`, {
      count,
      item_condition: itemCondition,
      shelf_mark_prefix: shelfMarkPrefix
    });
  }

  removeOneAvailableItem(bookId: number): Observable<any> {
    return this.http.post(`${this.apiUrl}/admin/books/${bookId}/items/remove_one`, {});
  }
}
