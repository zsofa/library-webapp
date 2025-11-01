import { Routes } from '@angular/router';
import { Login } from './components/login/login';
import { Dashboard } from './components/dashboard/dashboard';
import { Registration } from './components/registration/registration';
import { Forgotpwd } from './components/forgotpwd/forgotpwd';

export const routes: Routes = [
    {
        path: '',
        component: Login
    },
    {
        path: 'registration',
        component: Registration
    },
    {
        path: 'forgotpwd',
        component: Forgotpwd
    },
    {
        path: 'dashboard',
        component: Dashboard,
        children: [
            // {
            //     path: 'home',
            //     component: Dashboard
            // },
            // {
            //     path: 'books',
            //     component: Books
            // },
            // {
            //     path: 'requests',
            //     component: Requests
            // }
        ]
    }
];
