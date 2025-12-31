export interface Loan {
  loan_id: number;
  item_id: number;
  user_id: number;

  loan_date: string;
  due_date: string;
  return_date: string | null;

  fine_paid: number;

  book_id: number;
  title: string;
  author: string;
}
