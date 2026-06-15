import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { ApiService } from '../services/api.service';
import { AuthService } from '../services/auth.service';

@Component({
  selector: 'app-signin',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterLink],
  template: `
    <section class="card">
      <h2>Sign in</h2>
      <form [formGroup]="form" (ngSubmit)="submit()">
        <label>Email</label>
        <input type="email" formControlName="email" />

        <label>Password</label>
        <input type="password" formControlName="password" />

        <button type="submit" [disabled]="form.invalid || loading">Sign In</button>
      </form>
      <p class="err" *ngIf="error">{{ error }}</p>
      <a routerLink="/signup">Create a new account</a>
    </section>
  `,
})
export class SignInComponent {
  loading = false;
  error = '';

  private fb = inject(FormBuilder);

  form = this.fb.group({
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required]],
  });

  constructor(private api: ApiService, private auth: AuthService, private router: Router) {}

  submit() {
    if (this.form.invalid) return;
    this.loading = true;
    this.error = '';

    this.api.signIn(this.form.getRawValue() as any).subscribe({
      next: (res) => {
        this.auth.setToken(res.access_token);
        this.loading = false;
        this.router.navigateByUrl('/dashboard');
      },
      error: (err) => {
        this.error = err?.error?.detail || 'Invalid credentials.';
        this.loading = false;
      },
    });
  }
}


