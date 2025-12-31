export interface Book {
  id: number;
  title: string;
  author: string;

  available: boolean;
  extended: boolean;
  requested: boolean;
  borrowed: boolean;

  requestedAt?: Date | null;
  borrowedDate?: Date | null;
  expirationDate?: Date | null;

  waitlistCount?: number;
}

export interface ApiBook {
  book_id: number;
  title: string;
  author: string;
  isbn?: string;
  publication_year?: number;
  category?: string;
  total_items?: number;
  available_items?: number;

  // ✅ backendből jön
  waitlist_count?: number;
}
