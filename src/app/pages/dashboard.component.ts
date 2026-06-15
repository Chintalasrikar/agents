import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../services/auth.service';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <section class="dashboard-shell">
      <div class="hero">
        <p class="eyebrow">Choose your workspace</p>
        <h2>Two agents, one backend.</h2>
        <p class="hint">Pick the workflow you want to use after sign in.</p>
      </div>

      <div class="agent-grid">
        <a class="agent-card news" routerLink="/profile">
          <div class="agent-badge">News</div>
          <h3>News Agent</h3>
          <p>Manage topic subscriptions, delivery time, and daily digests.</p>
          <span class="agent-action">Open news workspace →</span>
        </a>

        <a class="agent-card cold" routerLink="/cold-email">
          <div class="agent-badge">Email</div>
          <h3>Cold Email Agent</h3>
          <p>Generate job application emails from your resume and a JD.</p>
          <span class="agent-action">Open cold email workspace →</span>
        </a>
      </div>
    </section>
  `,
})
export class DashboardComponent {
  constructor(private auth: AuthService, private router: Router) {
    if (!this.auth.getToken()) {
      this.router.navigateByUrl('/signin');
    }
  }
}
