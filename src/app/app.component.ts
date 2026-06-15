import { Component } from '@angular/core';
import { RouterLink, RouterOutlet } from '@angular/router';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, RouterLink],
  template: `
    <header class="topbar">
      <div class="brand">
        <span class="brand-mark">AG</span>
        <div>
          <h1>Agent Studio</h1>
          <p>News + Cold Email workflows</p>
        </div>
      </div>
      <nav>
        <a routerLink="/dashboard">Dashboard</a>
        <a routerLink="/signin">Sign In</a>
        <a routerLink="/signup">Sign Up</a>
      </nav>
    </header>
    <main class="container">
      <router-outlet></router-outlet>
    </main>
  `,
})
export class AppComponent {}
