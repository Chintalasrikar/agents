import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { ApiService } from '../services/api.service';
import { AuthService } from '../services/auth.service';

@Component({
  selector: 'app-profile',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  template: `
    <section class="card">
      <h2>User Profile</h2>
      <p class="hint">{{ email }}</p>

      <form [formGroup]="form" (ngSubmit)="save()">
        <label>Topic</label>
        <input type="text" formControlName="topic" />

        <label>Delivery Time</label>
        <input type="time" formControlName="delivery_time" />

        <button type="submit" [disabled]="form.invalid || loading">Save Profile</button>
      </form>

      <p class="ok" *ngIf="message">{{ message }}</p>
      <p class="err" *ngIf="error">{{ error }}</p>
      <button class="secondary" (click)="sendNow()">Send Digest Now</button>
      <button class="secondary" (click)="logout()">Logout</button>
    </section>
  `,
})
export class ProfileComponent implements OnInit {
  loading = false;
  email = '';
  message = '';
  error = '';

  private fb = inject(FormBuilder);

  form = this.fb.group({
    topic: ['', [Validators.required]],
    delivery_time: ['', [Validators.required]],
  });

  constructor(private api: ApiService, private auth: AuthService, private router: Router) {}

  ngOnInit() {
    const token = this.auth.getToken();
    if (!token) {
      this.router.navigateByUrl('/signin');
      return;
    }

    this.api.getProfile(token).subscribe({
      next: (profile) => {
        this.email = profile.email;
        this.form.patchValue({ topic: profile.topic, delivery_time: profile.delivery_time });
      },
      error: () => {
        this.auth.clearToken();
        this.router.navigateByUrl('/signin');
      },
    });
  }

  save() {
    const token = this.auth.getToken();
    if (!token || this.form.invalid) return;
    this.loading = true;
    this.message = '';
    this.error = '';

    this.api.updateProfile(token, this.form.getRawValue() as any).subscribe({
      next: () => {
        this.message = 'Profile updated.';
        this.loading = false;
      },
      error: (err) => {
        this.error = err?.error?.detail || 'Update failed.';
        this.loading = false;
      },
    });
  }

  sendNow() {
    const token = this.auth.getToken();
    if (!token) return;
    this.loading = true;
    this.message = '';
    this.error = '';

    this.api.sendDigestNow(token).subscribe({
      next: (res) => {
        this.message = res.message || 'Digest run completed.';
        this.loading = false;
      },
      error: (err) => {
        this.error = err?.error?.detail || 'Digest send failed.';
        this.loading = false;
      },
    });
  }

  logout() {
    this.auth.clearToken();
    this.router.navigateByUrl('/signin');
  }
}
