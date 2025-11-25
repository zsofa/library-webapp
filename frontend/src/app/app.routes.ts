import { Routes } from '@angular/router';
import { Login } from './components/login/login';
import { Dashboard } from './components/dashboard/dashboard';
import { Registration } from './components/registration/registration';
import { Forgotpwd } from './components/forgotpwd/forgotpwd';
import { Requests } from './components/dashboard/requests/requests';
import { Home } from './components/dashboard/home/home';
import { Mybooks } from './components/dashboard/mybooks/mybooks';
import { Catalogue } from './components/dashboard/catalogue/catalogue';

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
            {
                path: 'home',
                component: Home
            },
            {
                path: 'mybooks',
                component: Mybooks
            },
            {
                path: 'requests',
                component: Requests
            },
            {
                path: 'catalogue',
                component: Catalogue
            }
        ]
    }
];
