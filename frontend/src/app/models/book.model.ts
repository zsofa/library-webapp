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
}
