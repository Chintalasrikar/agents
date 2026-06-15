import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { ApiService, ColdEmailDraft, ColdEmailProfile } from '../services/api.service';
import { AuthService } from '../services/auth.service';

type ChatRole = 'assistant' | 'user';

type ChatMessage = {
  role: ChatRole;
  text: string;
};

@Component({
  selector: 'app-cold-email',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  styles: [`
    :host {
      display: block;
      min-height: calc(100vh - 120px);
    }

    .workspace {
      display: grid;
      grid-template-columns: minmax(0, 1fr);
      min-height: calc(100vh - 140px);
      gap: 1rem;
    }

    .workspace-shell {
      display: grid;
      grid-template-rows: auto 1fr auto;
      min-height: calc(100vh - 160px);
      background: rgba(255, 255, 255, 0.78);
      border: 1px solid rgba(148, 163, 184, 0.25);
      border-radius: 24px;
      backdrop-filter: blur(16px);
      box-shadow: 0 20px 60px rgba(15, 23, 42, 0.08);
      overflow: hidden;
    }

    .workspace-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 1rem;
      padding: 1.25rem 1.25rem 1rem;
      border-bottom: 1px solid rgba(148, 163, 184, 0.2);
      background: linear-gradient(180deg, rgba(248, 250, 252, 0.95), rgba(255, 255, 255, 0.85));
      position: relative;
    }

    .header-copy h2 {
      margin: 0;
      font-size: 1.5rem;
    }

    .header-copy p {
      margin: 0.4rem 0 0;
    }

    .profile-trigger {
      position: relative;
      flex: 0 0 auto;
    }

    .avatar-btn {
      width: 48px;
      height: 48px;
      border-radius: 999px;
      border: 1px solid #cbd5e1;
      background: linear-gradient(135deg, #0f172a, #1d4ed8);
      color: #fff;
      display: grid;
      place-items: center;
      font-weight: 800;
      cursor: pointer;
    }

    .profile-menu {
      position: absolute;
      top: calc(100% + 0.75rem);
      right: 0;
      width: 320px;
      background: #fff;
      border: 1px solid rgba(148, 163, 184, 0.2);
      border-radius: 18px;
      box-shadow: 0 24px 60px rgba(15, 23, 42, 0.16);
      padding: 1rem;
      z-index: 8;
    }

    .profile-menu h4 {
      margin: 0 0 0.35rem;
    }

    .profile-row {
      display: flex;
      justify-content: space-between;
      gap: 0.75rem;
      margin-top: 0.45rem;
      font-size: 0.92rem;
      color: #334155;
      word-break: break-word;
    }

    .profile-menu .actions {
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
      margin-top: 1rem;
    }

    .profile-editor {
      padding: 1rem 1.25rem 0.25rem;
      border-bottom: 1px solid rgba(148, 163, 184, 0.18);
      background: rgba(248, 250, 252, 0.55);
    }

    .profile-editor-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 1rem;
    }

    .profile-editor-grid .full {
      grid-column: 1 / -1;
    }

    .chat-area {
      display: grid;
      grid-template-rows: 1fr auto;
      min-height: 0;
    }

    .chat-log {
      padding: 1.25rem;
      overflow: auto;
      display: flex;
      flex-direction: column;
      gap: 0.9rem;
      min-height: 0;
    }

    .chat-row {
      display: flex;
    }

    .chat-row.user {
      justify-content: flex-end;
    }

    .chat-row.assistant {
      justify-content: flex-start;
    }

    .bubble {
      max-width: min(820px, 92%);
      border-radius: 20px;
      padding: 0.95rem 1rem;
      line-height: 1.65;
      white-space: pre-wrap;
      border: 1px solid #dbe4f0;
      background: #fff;
      box-shadow: 0 4px 16px rgba(15, 23, 42, 0.05);
    }

    .chat-row.user .bubble {
      background: linear-gradient(180deg, #1d4ed8, #0f5bd4);
      color: #fff;
      border-color: #1d4ed8;
    }

    .bubble-meta {
      font-size: 0.72rem;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      opacity: 0.7;
      margin-bottom: 0.4rem;
    }

    .bubble-title {
      font-weight: 700;
      margin-bottom: 0.35rem;
    }

    .composer {
      border-top: 1px solid rgba(148, 163, 184, 0.18);
      padding: 1rem 1.25rem 1.25rem;
      background: linear-gradient(180deg, rgba(255, 255, 255, 0.88), rgba(248, 250, 252, 0.96));
    }

    .composer-grid {
      display: grid;
      grid-template-columns: 1.2fr 0.8fr;
      gap: 0.9rem;
      margin-bottom: 0.9rem;
    }

    .composer-actions {
      display: flex;
      gap: 0.75rem;
      flex-wrap: wrap;
      margin-top: 0.9rem;
    }

    .quick-actions {
      display: flex;
      gap: 0.5rem;
      flex-wrap: wrap;
      margin-bottom: 0.75rem;
    }

    .chip {
      border: 1px solid #cbd5e1;
      background: #fff;
      color: #0f172a;
      border-radius: 999px;
      padding: 0.45rem 0.75rem;
      cursor: pointer;
      font-size: 0.9rem;
      margin-top: 0;
    }

    .status {
      margin-top: 0.75rem;
    }

    @media (max-width: 760px) {
      .workspace-shell {
        min-height: calc(100vh - 120px);
      }

      .profile-menu {
        width: min(320px, calc(100vw - 2rem));
      }

      .profile-editor-grid,
      .composer-grid {
        grid-template-columns: 1fr;
      }
    }
  `],
  template: `
    <section class="workspace">
      <div class="workspace-shell">
        <header class="workspace-header">
          <div class="header-copy">
            <h2>Cold Email Agent</h2>
            <p class="hint">Paste a job description, review the draft, then approve or revise in chat.</p>
          </div>

          <div class="profile-trigger">
            <button class="avatar-btn" type="button" (click)="toggleProfileMenu()" [attr.aria-expanded]="profileMenuOpen">
              {{ avatarInitial }}
            </button>

            <div class="profile-menu" *ngIf="profileMenuOpen">
              <h4>{{ profile?.name || 'Profile' }}</h4>
              <div class="profile-row"><span>Email</span><span>{{ profile?.email || userEmail || 'Not set' }}</span></div>
              <div class="profile-row"><span>LinkedIn</span><span>{{ profile?.linkedin_url || 'Not set' }}</span></div>
              <div class="profile-row"><span>GitHub</span><span>{{ profile?.github_url || 'Not set' }}</span></div>
              <div class="profile-row"><span>Mobile</span><span>{{ profile?.mobile_number || 'Not set' }}</span></div>
              <div class="profile-row"><span>Resume</span><span>{{ profile?.resume_path || 'Not uploaded' }}</span></div>

              <div class="actions">
                <button type="button" class="secondary" (click)="openProfileEditor()">Edit profile</button>
                <button type="button" class="secondary" (click)="focusResume()">Update resume</button>
                <button type="button" class="secondary" (click)="logout()">Logout</button>
              </div>
            </div>
          </div>
        </header>

        <section class="profile-editor" *ngIf="showProfileEditor || !profile">
          <form [formGroup]="profileForm" (ngSubmit)="saveProfile()">
            <div class="profile-editor-grid">
              <div>
                <label>Name</label>
                <input type="text" formControlName="name" />
              </div>

              <div>
                <label>LinkedIn URL</label>
                <input type="url" formControlName="linkedin_url" />
              </div>

              <div>
                <label>GitHub URL</label>
                <input type="url" formControlName="github_url" />
              </div>

              <div>
                <label>Mobile Number</label>
                <input type="text" formControlName="mobile_number" />
              </div>

              <div class="full">
                <label>Resume PDF</label>
                <input #resumeInput type="file" accept="application/pdf" (change)="onResumeSelected($event)" />
              </div>
            </div>

            <div class="composer-actions">
              <button type="submit" [disabled]="profileForm.invalid || loading || !selectedResumeFile">Save Profile</button>
              <button type="button" class="secondary" (click)="updateResume()" [disabled]="loading || !selectedResumeFile || !profile">
                Update Resume Only
              </button>
              <button type="button" class="secondary" (click)="showProfileEditor = false" *ngIf="profile">Close</button>
            </div>
          </form>
        </section>

        <section class="chat-area">
          <div class="chat-log" #chatLog>
            <div *ngFor="let message of messages" class="chat-row" [class.user]="message.role === 'user'" [class.assistant]="message.role === 'assistant'">
              <div class="bubble">
                <div class="bubble-meta">{{ message.role === 'user' ? 'You' : 'Agent' }}</div>
                <div *ngIf="message.role === 'assistant' && message.title" class="bubble-title">{{ message.title }}</div>
                <div>{{ message.text }}</div>
              </div>
            </div>

            <div class="status" *ngIf="loading">
              <div class="bubble">
                <div class="bubble-meta">Agent</div>
                Typing...
              </div>
            </div>
          </div>

          <div class="composer">
            <div class="quick-actions" *ngIf="draft">
              <button type="button" class="chip" (click)="approveDraft()">Approve</button>
              <button type="button" class="chip" (click)="rejectDraft()">Reject</button>
              <button type="button" class="chip" (click)="prefillFeedback('Make it shorter and more confident.')">Shorter</button>
              <button type="button" class="chip" (click)="prefillFeedback('Make it more formal and polished.')">More formal</button>
            </div>

            <form [formGroup]="chatForm" (ngSubmit)="submitChat()">
              <div class="composer-grid">
                <div>
                  <label>Recruiter Email <span class="hint">(optional if present in JD)</span></label>
                  <input type="email" formControlName="recruiter_email" placeholder="recruiter@company.com" />
                </div>
                <div>
                  <label>Job Title</label>
                  <input type="text" formControlName="job_title" placeholder="AI Engineer" />
                </div>
              </div>

              <label>{{ draft ? 'Tell me what to change' : 'Paste the job description' }}</label>
              <textarea
                rows="6"
                formControlName="message"
                [placeholder]="draft ? 'Example: make it more concise and mention Python skills' : 'Paste the JD here'"
              ></textarea>

              <div class="composer-actions">
                <button type="submit" [disabled]="chatForm.invalid || loading || !profile">
                  {{ draft ? 'Revise Draft' : 'Generate Draft' }}
                </button>
                <button type="button" class="secondary" (click)="openProfileEditor()">Profile</button>
                <button type="button" class="secondary" (click)="sendEmail()" [disabled]="!draft || loading">Approve & Send</button>
              </div>
            </form>

            <p class="ok" *ngIf="message">{{ message }}</p>
            <p class="err" *ngIf="error">{{ error }}</p>
          </div>
        </section>
      </div>
    </section>
  `,
})
export class ColdEmailComponent implements OnInit {
  private readonly initialAssistantMessage = 'Upload your resume, then paste a job description and I will draft a job application email for you.';

  loading = false;
  message = '';
  error = '';
  profile: ColdEmailProfile | null = null;
  draft: ColdEmailDraft | null = null;
  selectedResumeFile: File | null = null;
  messages: Array<ChatMessage & { title?: string }> = [
    {
      role: 'assistant',
      text: this.initialAssistantMessage,
    },
  ];
  profileMenuOpen = false;
  showProfileEditor = false;
  currentJobDescription = '';
  currentJobTitle = '';
  userEmail = '';

  private fb = inject(FormBuilder);

  profileForm = this.fb.group({
    name: ['', [Validators.required]],
    linkedin_url: [''],
    github_url: [''],
    mobile_number: [''],
  });

  chatForm = this.fb.group({
    recruiter_email: [''],
    job_title: [''],
    message: ['', [Validators.required]],
  });

  constructor(private api: ApiService, private auth: AuthService, private router: Router) {}

  ngOnInit() {
    const token = this.auth.getToken();
    if (!token) {
      this.router.navigateByUrl('/signin');
      return;
    }

    this.api.getColdEmailProfile(token).subscribe({
      next: (profile) => {
        this.profile = profile;
        this.userEmail = profile.email;
        this.profileForm.patchValue({
          name: profile.name,
          linkedin_url: profile.linkedin_url,
          github_url: profile.github_url,
          mobile_number: profile.mobile_number,
        });
      },
      error: () => {
        this.profile = null;
        this.showProfileEditor = true;
      },
    });
  }

  get avatarInitial(): string {
    const source = this.profile?.name || this.userEmail || 'A';
    return source.trim().charAt(0).toUpperCase();
  }

  toggleProfileMenu() {
    this.profileMenuOpen = !this.profileMenuOpen;
  }

  openProfileEditor() {
    this.showProfileEditor = true;
    this.profileMenuOpen = false;
    if (this.profile) {
      this.profileForm.patchValue({
        name: this.profile.name,
        linkedin_url: this.profile.linkedin_url,
        github_url: this.profile.github_url,
        mobile_number: this.profile.mobile_number,
      });
    }
  }

  focusResume() {
    this.showProfileEditor = true;
    this.profileMenuOpen = false;
  }

  onResumeSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    this.selectedResumeFile = input.files && input.files.length > 0 ? input.files[0] : null;
  }

  saveProfile() {
    const token = this.auth.getToken();
    if (!token || this.profileForm.invalid || !this.selectedResumeFile) return;

    this.loading = true;
    this.message = '';
    this.error = '';

    this.api.saveColdEmailProfile(token, { ...(this.profileForm.getRawValue() as any), resume: this.selectedResumeFile }).subscribe({
      next: (profile) => {
        this.profile = profile;
        this.userEmail = profile.email;
        this.showProfileEditor = false;
        this.messages.push({ role: 'assistant', text: 'Profile saved. Paste a job description whenever you are ready.' });
        this.loading = false;
      },
      error: (err) => {
        this.error = this.formatApiError(err, 'Profile save failed.');
        this.loading = false;
      },
    });
  }

  updateResume() {
    const token = this.auth.getToken();
    if (!token || !this.selectedResumeFile || !this.profile) return;

    this.loading = true;
    this.message = '';
    this.error = '';

    this.api.updateColdEmailResume(token, this.selectedResumeFile).subscribe({
      next: (profile) => {
        this.profile = profile;
        this.userEmail = profile.email;
        this.messages.push({ role: 'assistant', text: 'Resume updated successfully.' });
        this.loading = false;
      },
      error: (err) => {
        this.error = this.formatApiError(err, 'Resume update failed.');
        this.loading = false;
      },
    });
  }

  submitChat() {
    const token = this.auth.getToken();
    if (!token || this.chatForm.invalid || !this.profile) return;

    const payload = this.chatForm.getRawValue() as any;
    const text = (payload.message || '').trim();
    if (!text) return;

    this.loading = true;
    this.message = '';
    this.error = '';
    this.messages.push({ role: 'user', text });

    const recruiterEmail = (payload.recruiter_email || '').trim() || null;
    const jobTitle = (payload.job_title || '').trim();

    if (!this.draft) {
      this.currentJobDescription = text;
      this.currentJobTitle = jobTitle;

      this.api.createColdEmailDraft(token, {
        recruiter_email: recruiterEmail,
        job_title: jobTitle,
        job_description: text,
      }).subscribe({
        next: (draft) => {
          this.applyDraft(draft, 'I drafted a job application email. You can approve it, reject it, or ask for changes.');
          this.chatForm.patchValue({ message: '' });
          this.loading = false;
        },
        error: (err) => {
          this.error = this.formatApiError(err, 'Draft generation failed.');
          this.loading = false;
        },
      });
      return;
    }

    this.api.reviseColdEmailDraft(token, {
      recruiter_email: recruiterEmail || this.draft.recruiter_email,
      job_title: this.currentJobTitle || this.draft.job_title,
      job_description: this.currentJobDescription,
      subject: this.draft.subject,
      body: this.draft.body,
      feedback: text,
    }).subscribe({
      next: (draft) => {
        this.applyDraft(draft, 'I updated the draft based on your changes.');
        this.chatForm.patchValue({ message: '' });
        this.loading = false;
      },
      error: (err) => {
        this.error = this.formatApiError(err, 'Regenerate failed.');
        this.loading = false;
      },
    });
  }

  rejectDraft() {
    this.messages.push({
      role: 'assistant',
      text: 'Sure. Tell me what you want to change in the chat box, and I will rewrite the email.',
    });
  }

  prefillFeedback(text: string) {
    this.chatForm.patchValue({ message: text });
  }

  approveDraft() {
    if (!this.draft) return;
    this.sendEmail();
  }

  sendEmail() {
    const token = this.auth.getToken();
    if (!token || !this.draft || !this.profile) return;

    this.loading = true;
    this.message = '';
    this.error = '';

    this.api.sendColdEmail(token, {
      recruiter_email: this.draft.recruiter_email,
      subject: this.draft.subject,
      body: this.draft.body,
    }).subscribe({
      next: (res) => {
        this.message = res.message || 'Cold email sent.';
        this.resetConversation('Email sent successfully. Paste a new JD to start a fresh draft.');
        this.loading = false;
      },
      error: (err) => {
        this.error = this.formatApiError(err, 'Send failed.');
        this.loading = false;
      },
    });
  }

  logout() {
    this.auth.clearToken();
    this.router.navigateByUrl('/signin');
  }

  private applyDraft(draft: ColdEmailDraft, note: string) {
    this.draft = draft;
    this.messages.push({
      role: 'assistant',
      title: draft.subject,
      text: `${note}\n\n${draft.body}`,
    });
    this.profileMenuOpen = false;
  }

  private resetConversation(note?: string) {
    this.draft = null;
    this.currentJobDescription = '';
    this.currentJobTitle = '';
    this.chatForm.reset({ recruiter_email: '', job_title: '', message: '' });
    this.messages = [
      {
        role: 'assistant',
        text: this.initialAssistantMessage,
      },
    ];
    if (note) {
      this.messages.push({ role: 'assistant', text: note });
    }
    this.profileMenuOpen = false;
  }

  private formatApiError(err: any, fallback: string): string {
    const detail = err?.error?.detail;
    if (typeof detail === 'string' && detail.trim()) {
      return detail;
    }
    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0];
      if (typeof first === 'string') {
        return first;
      }
      if (first?.msg) {
        return String(first.msg);
      }
    }
    return fallback;
  }
}
