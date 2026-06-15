import { Routes } from '@angular/router';
import { SignInComponent } from './pages/signin.component';
import { SignUpComponent } from './pages/signup.component';
import { ProfileComponent } from './pages/profile.component';
import { ColdEmailComponent } from './pages/cold-email.component';
import { DashboardComponent } from './pages/dashboard.component';

export const routes: Routes = [
  { path: '', redirectTo: 'signin', pathMatch: 'full' },
  { path: 'signin', component: SignInComponent },
  { path: 'signup', component: SignUpComponent },
  { path: 'dashboard', component: DashboardComponent },
  { path: 'profile', component: ProfileComponent },
  { path: 'cold-email', component: ColdEmailComponent },
];
