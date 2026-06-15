import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { environment } from '../../environments/environment';

export type Profile = {
  email: string;
  topic: string;
  delivery_time: string;
};

export type ColdEmailProfile = {
  email: string;
  name: string;
  linkedin_url: string;
  github_url: string;
  mobile_number: string;
  resume_path: string;
};

export type ColdEmailDraft = {
  recruiter_email: string;
  subject: string;
  body: string;
  job_title: string;
};

@Injectable({ providedIn: 'root' })
export class ApiService {
  private baseUrl = environment.apiUrl;

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

  getColdEmailProfile(token: string) {
    return this.http.get<ColdEmailProfile>(`${this.baseUrl}/cold-email/profile`, {
      headers: new HttpHeaders({ Authorization: `Bearer ${token}` }),
    });
  }

  saveColdEmailProfile(
    token: string,
    payload: {
      name: string;
      linkedin_url: string;
      github_url: string;
      mobile_number: string;
      resume: File;
    },
  ) {
    const formData = new FormData();
    formData.append('name', payload.name);
    formData.append('linkedin_url', payload.linkedin_url);
    formData.append('github_url', payload.github_url);
    formData.append('mobile_number', payload.mobile_number);
    formData.append('resume', payload.resume);

    return this.http.post<ColdEmailProfile>(`${this.baseUrl}/cold-email/profile`, formData, {
      headers: new HttpHeaders({ Authorization: `Bearer ${token}` }),
    });
  }

  updateColdEmailResume(token: string, resume: File) {
    const formData = new FormData();
    formData.append('resume', resume);
    return this.http.put<ColdEmailProfile>(`${this.baseUrl}/cold-email/profile/resume`, formData, {
      headers: new HttpHeaders({ Authorization: `Bearer ${token}` }),
    });
  }

  createColdEmailDraft(
    token: string,
    payload: { recruiter_email?: string; job_title: string; job_description: string },
  ) {
    return this.http.post<ColdEmailDraft>(`${this.baseUrl}/cold-email/draft`, payload, {
      headers: new HttpHeaders({ Authorization: `Bearer ${token}` }),
    });
  }

  reviseColdEmailDraft(
    token: string,
    payload: {
      recruiter_email?: string;
      job_title: string;
      job_description: string;
      subject: string;
      body: string;
      feedback: string;
    },
  ) {
    return this.http.post<ColdEmailDraft>(`${this.baseUrl}/cold-email/draft/revise`, payload, {
      headers: new HttpHeaders({ Authorization: `Bearer ${token}` }),
    });
  }

  sendColdEmail(
    token: string,
    payload: { recruiter_email: string; subject: string; body: string },
  ) {
    return this.http.post<{ message: string; message_id: string }>(`${this.baseUrl}/cold-email/send`, payload, {
      headers: new HttpHeaders({ Authorization: `Bearer ${token}` }),
    });
  }
}
