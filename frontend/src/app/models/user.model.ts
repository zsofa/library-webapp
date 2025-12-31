export interface User {
  user_id: number;
  email: string;
  name?: string;
  role?: string;
  library_id?: number;

  address?: string;
  phoneNumber?: string;
  createdAt?: Date;
}

