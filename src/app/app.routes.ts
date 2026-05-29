import { Routes } from '@angular/router';
import { SignInComponent } from './pages/signin.component';
import { SignUpComponent } from './pages/signup.component';
import { ProfileComponent } from './pages/profile.component';

export const routes: Routes = [
  { path: '', redirectTo: 'signin', pathMatch: 'full' },
  { path: 'signin', component: SignInComponent },
  { path: 'signup', component: SignUpComponent },
  { path: 'profile', component: ProfileComponent },
];
