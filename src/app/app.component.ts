import { Component } from '@angular/core';
import { RouterLink, RouterOutlet } from '@angular/router';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, RouterLink],
  template: `
    <header class="topbar">
      <h1>News Agent</h1>
      <nav>
        <a routerLink="/signin">Sign In</a>
        <a routerLink="/signup">Sign Up</a>
        <a routerLink="/profile">Profile</a>
      </nav>
    </header>
    <main class="container">
      <router-outlet></router-outlet>
    </main>
  `,
})
export class AppComponent {}
