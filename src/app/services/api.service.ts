import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';

export type Profile = {
  email: string;
  topic: string;
  delivery_time: string;
};

@Injectable({ providedIn: 'root' })
export class ApiService {
  private baseUrl = 'http://127.0.0.1:8000';

  constructor(private http: HttpClient) {}

  signUp(payload: { email: string; password: string; topic: string; delivery_time: string }) {
    return this.http.post<{ message: string }>(`${this.baseUrl}/auth/signup`, payload);
  }

  signIn(payload: { email: string; password: string }) {
    return this.http.post<{ access_token: string }>(`${this.baseUrl}/auth/signin`, payload);
  }

  getProfile(token: string) {
    return this.http.get<Profile>(`${this.baseUrl}/users/me`, {
      headers: new HttpHeaders({ Authorization: `Bearer ${token}` }),
    });
  }

  updateProfile(token: string, payload: { topic: string; delivery_time: string }) {
    return this.http.put<{ message: string }>(`${this.baseUrl}/users/me`, payload, {
      headers: new HttpHeaders({ Authorization: `Bearer ${token}` }),
    });
  }

  sendDigestNow(token: string) {
    return this.http.post<{ message: string }>(`${this.baseUrl}/digest/send-now`, {}, {
      headers: new HttpHeaders({ Authorization: `Bearer ${token}` }),
    });
  }
}
