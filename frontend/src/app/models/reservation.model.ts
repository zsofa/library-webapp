export interface Reservation {
  reservation_id: number;
  book_id: number;
  user_id: number;
  queue_number: number;
  reservation_date: string;
  expiry_date: string | null;
  status: 'pending' | 'ready' | 'expired' | 'fulfilled';

  title?: string;
  author?: string;
  available_items?: number;
}

