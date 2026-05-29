import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { ApiService } from '../services/api.service';

@Component({
  selector: 'app-signup',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterLink],
  template: `
    <section class="card">
      <h2>Create account</h2>
      <form [formGroup]="form" (ngSubmit)="submit()">
        <label>Email</label>
        <input type="email" formControlName="email" />

        <label>Password</label>
        <input type="password" formControlName="password" />

        <label>Topic</label>
        <input type="text" formControlName="topic" placeholder="AI / Healthcare / IPL" />

        <label>Delivery Time</label>
        <input type="time" formControlName="delivery_time" />

        <button type="submit" [disabled]="form.invalid || loading">Sign Up</button>
      </form>
      <p class="ok" *ngIf="message">{{ message }}</p>
      <p class="err" *ngIf="error">{{ error }}</p>
      <a routerLink="/signin">Already have an account?</a>
    </section>
  `,
})
export class SignUpComponent {
  loading = false;
  message = '';
  error = '';

  private fb = inject(FormBuilder);

  form = this.fb.group({
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required, Validators.minLength(6)]],
    topic: ['', [Validators.required]],
    delivery_time: ['08:00', [Validators.required]],
  });

  constructor(private api: ApiService, private router: Router) {}

  submit() {
    if (this.form.invalid) return;
    this.loading = true;
    this.error = '';
    this.message = '';

    this.api.signUp(this.form.getRawValue() as any).subscribe({
      next: () => {
        this.message = 'Account created successfully.';
        this.loading = false;
        this.router.navigateByUrl('/signin');
      },
      error: (err) => {
        this.error = err?.error?.detail || 'Signup failed.';
        this.loading = false;
      },
    });
  }
}


