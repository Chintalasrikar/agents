import { Injectable } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private key = 'news_agent_token';

  setToken(token: string) {
    localStorage.setItem(this.key, token);
  }

  getToken(): string {
    return localStorage.getItem(this.key) || '';
  }

  clearToken() {
    localStorage.removeItem(this.key);
  }
}
