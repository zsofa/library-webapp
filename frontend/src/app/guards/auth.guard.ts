import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { Auth } from '../services/auth';

export const adminGuard: CanActivateFn = () => {
  const auth = inject(Auth);
  const router = inject(Router);

  if (!auth.isLoggedIn()) {
    router.navigateByUrl('/');
    return false;
  }

  if (!auth.isAdmin()) {
    router.navigateByUrl('/dashboard/home');
    return false;
  }

  return true;
};
