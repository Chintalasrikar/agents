import base64
import io
import json
import logging
import os
import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Optional

import psycopg2
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from groq import Groq

try:
    from pypdf import PdfReader
except ImportError:  # pragma: no cover - optional dependency
    PdfReader = None

load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
TOKEN_FILE = Path("cold_email_token.json")
RESUME_DIR = Path("resumes")


@dataclass
class ColdEmailProfile:
    email: str
    name: str
    linkedin_url: str
    github_url: str
    mobile_number: str
    resume_path: str
    resume_text: str = ""


@dataclass
class ColdEmailDraft:
    subject: str
    body: str
    recruiter_email: str
    user_email: str
    job_description: str
    job_title: str = ""


def setup_logging() -> None:
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    log_file = os.getenv("LOG_FILE", str(logs_dir / "cold_email_agent.log"))
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    handlers = [
        logging.StreamHandler(),
        RotatingFileHandler(log_file, maxBytes=2_000_000, backupCount=5, encoding="utf-8"),
    ]
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=handlers,
        force=True,
    )


def get_db_connection():
    database_url = os.getenv("DATABASE_URL", "").strip()
    if database_url:
        return psycopg2.connect(database_url)
    # return psycopg2.connect(
    #     host=os.getenv("PGHOST", "localhost"),
    #     port=int(os.getenv("PGPORT", "5432")),
    #     dbname=os.getenv("PGDATABASE", "news_agent"),
    #     user=os.getenv("PGUSER", "postgres"),
    #     password=os.getenv("PGPASSWORD", ""),
    # )


def init_db() -> None:
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS cold_email_profiles (
                    email TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    linkedin_url TEXT NOT NULL DEFAULT '',
                    github_url TEXT NOT NULL DEFAULT '',
                    mobile_number TEXT NOT NULL DEFAULT '',
                    resume_path TEXT NOT NULL DEFAULT '',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """
            )
            cur.execute("ALTER TABLE cold_email_profiles ADD COLUMN IF NOT EXISTS resume_path TEXT;")
        conn.commit()


def normalize_email(value: str) -> str:
    value = (value or "").strip().lower()
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", value):
        raise ValueError("Invalid email format.")
    return value


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def normalize_multiline(value: str) -> str:
    return "\n".join(line.rstrip() for line in (value or "").strip().splitlines()).strip()


def extract_email_addresses(text: str) -> list[str]:
    seen: list[str] = []
    for match in re.findall(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", text or ""):
        email = match.lower()
        if email not in seen:
            seen.append(email)
    return seen


def infer_recruiter_email(job_description: str) -> Optional[str]:
    emails = extract_email_addresses(job_description)
    return emails[0] if emails else None


def ensure_resume_dir() -> Path:
    RESUME_DIR.mkdir(exist_ok=True)
    return RESUME_DIR


def save_uploaded_resume_to_folder(user_email: str, filename: str, pdf_bytes: bytes) -> str:
    source_name = Path(filename or "resume.pdf").name
    if Path(source_name).suffix.lower() != ".pdf":
        raise ValueError("Resume must be a PDF file.")
    destination_dir = ensure_resume_dir()
    destination_path = destination_dir / source_name
    destination_path.write_bytes(pdf_bytes)
    return str(destination_path)


def save_resume_to_folder(user_email: str, source_pdf_path: str) -> str:
    source_path = Path(source_pdf_path).expanduser().resolve()
    if not source_path.exists():
        raise ValueError(f"Resume file not found: {source_path}")
    if source_path.suffix.lower() != ".pdf":
        raise ValueError("Resume must be a PDF file.")
    destination_dir = ensure_resume_dir()
    destination_path = destination_dir / source_path.name
    shutil.copy2(source_path, destination_path)
    return str(destination_path)


def extract_resume_text_from_pdf(pdf_bytes: bytes) -> str:
    if PdfReader is None:
        raise RuntimeError("PDF support is missing. Install `pypdf` to extract resume text.")
    reader = PdfReader(io.BytesIO(pdf_bytes))
    pages = []
    for page in reader.pages:
        page_text = page.extract_text() or ""
        if page_text.strip():
            pages.append(page_text)
    return normalize_multiline("\n".join(pages))


def load_resume_text_from_path(pdf_path: str) -> str:
    path = Path(pdf_path).expanduser().resolve()
    if not path.exists():
        raise ValueError(f"Resume file not found: {path}")
    if path.suffix.lower() != ".pdf":
        raise ValueError("Resume must be a PDF file.")
    pdf_bytes = path.read_bytes()
    resume_text = extract_resume_text_from_pdf(pdf_bytes)
    if not resume_text:
        raise ValueError("Could not extract text from the PDF.")
    return resume_text


def upsert_profile(profile: ColdEmailProfile) -> None:
    init_db()
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO cold_email_profiles (
                    email, name, linkedin_url, github_url, mobile_number, resume_path
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (email)
                DO UPDATE SET
                    name = EXCLUDED.name,
                    linkedin_url = EXCLUDED.linkedin_url,
                    github_url = EXCLUDED.github_url,
                    mobile_number = EXCLUDED.mobile_number,
                    resume_path = EXCLUDED.resume_path,
                    updated_at = NOW();
                """,
                (
                    normalize_email(profile.email),
                    normalize_text(profile.name),
                    normalize_text(profile.linkedin_url),
                    normalize_text(profile.github_url),
                    normalize_text(profile.mobile_number),
                    normalize_text(profile.resume_path),
                ),
            )
        conn.commit()


def upsert_profile_with_pdf(
    *,
    email: str,
    name: str,
    linkedin_url: str,
    github_url: str,
    mobile_number: str,
    pdf_filename: str,
    pdf_bytes: bytes,
) -> ColdEmailProfile:
    resume_path = save_uploaded_resume_to_folder(email, pdf_filename, pdf_bytes)
    resume_text = load_resume_text_from_path(resume_path)
    profile = ColdEmailProfile(
        email=normalize_email(email),
        name=normalize_text(name),
        linkedin_url=normalize_text(linkedin_url),
        github_url=normalize_text(github_url),
        mobile_number=normalize_text(mobile_number),
        resume_path=resume_path,
        resume_text=resume_text,
    )
    upsert_profile(profile)
    return profile


def get_profile(user_email: str) -> Optional[ColdEmailProfile]:
    init_db()
    user_email = normalize_email(user_email)
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT email, name, linkedin_url, github_url, mobile_number, resume_path
                FROM cold_email_profiles
                WHERE email = %s
                """,
                (user_email,),
            )
            row = cur.fetchone()
    if not row:
        return None
    return ColdEmailProfile(
        email=row[0],
        name=row[1],
        linkedin_url=row[2] or "",
        github_url=row[3] or "",
        mobile_number=row[4] or "",
        resume_path=row[5] or "",
        resume_text=load_resume_text_from_path(row[5]) if row[5] else "",
    )


def get_groq_client() -> Groq | None:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        logging.warning("GROQ_API_KEY missing. Draft generation will use fallback templates.")
        return None
    return Groq(api_key=api_key)


def infer_job_title(job_description: str) -> str:
    first_line = normalize_text(job_description.splitlines()[0] if job_description else "")
    return first_line[:80] if first_line else "Job Opportunity"


def build_resume_context(profile: ColdEmailProfile) -> str:
    resume_text = profile.resume_text or (load_resume_text_from_path(profile.resume_path) if profile.resume_path else "")
    return (
        f"Name: {profile.name}\n"
        f"Email: {profile.email}\n"
        f"LinkedIn: {profile.linkedin_url or 'N/A'}\n"
        f"GitHub: {profile.github_url or 'N/A'}\n"
        f"Mobile: {profile.mobile_number or 'N/A'}\n"
        f"Resume path: {profile.resume_path or 'N/A'}\n\n"
        f"Resume:\n{resume_text}"
    )


def build_fallback_draft(
    profile: ColdEmailProfile,
    recruiter_email: str,
    job_description: str,
    job_title: str = "",
) -> ColdEmailDraft:
    recruiter_email = normalize_email(recruiter_email)
    job_title = normalize_text(job_title) or infer_job_title(job_description)
    subject = f"Application for {job_title} - {profile.name}"
    body = (
        f"Dear Hiring Team,\n\n"
        f"I am excited to apply for the {job_title} position.\n\n"
        f"After reviewing the job description, I believe my background and projects align well with the role requirements. "
        f"I have hands-on experience in relevant technical areas and am confident I can contribute meaningfully to your team.\n\n"
        f"Please find my resume attached for your review. I would welcome the opportunity to discuss my application further.\n\n"
        f"Best regards,\n"
        f"{profile.name}\n"
        f"{profile.email}\n"
        f"{profile.linkedin_url or 'N/A'}\n"
        f"{profile.github_url or 'N/A'}\n"
        f"{profile.mobile_number or 'N/A'}"
    )
    return ColdEmailDraft(
        subject=subject,
        body=body,
        recruiter_email=recruiter_email,
        user_email=profile.email,
        job_description=job_description,
        job_title=job_title,
    )


def parse_json_object(raw: str) -> Dict[str, Any]:
    raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def generate_cold_email_draft(
    profile: ColdEmailProfile,
    recruiter_email: str,
    job_description: str,
    job_title: str = "",
) -> ColdEmailDraft:
    recruiter_email = normalize_email(recruiter_email)
    job_description = normalize_multiline(job_description)
    job_title = normalize_text(job_title) or infer_job_title(job_description)

    client = get_groq_client()
    if not client:
        return build_fallback_draft(profile, recruiter_email, job_description, job_title)

    model = os.getenv("MODEL", "llama-3.3-70b-versatile")
    prompt = (
        "Write a professional job application email to a recruiter or hiring manager.\n"
        "This is an application email, not a referral request.\n"
        "Use only the resume and job description. Do not invent experience.\n"
        "Return strict JSON only in this format:\n"
        "{\"subject\":\"...\",\"body\":\"...\"}\n"
        "The body should be concise, confident, and feel human-written.\n"
        "Mention that the resume is attached.\n"
        "Use this signature information exactly:\n"
        f"Name: {profile.name}\n"
        f"Email: {profile.email}\n"
        f"LinkedIn: {profile.linkedin_url or 'N/A'}\n"
        f"GitHub: {profile.github_url or 'N/A'}\n"
        f"Mobile: {profile.mobile_number or 'N/A'}\n"
        f"Recruiter email: {recruiter_email}\n"
        f"Job title: {job_title}\n"
        f"Job description:\n{job_description}\n\n"
        f"Resume context:\n{build_resume_context(profile)}"
    )

    try:
        response = client.chat.completions.create(
            model=model,
            temperature=0.2,
            messages=[{"role": "user", "content": prompt}],
        )
        data = parse_json_object(response.choices[0].message.content.strip())
        subject = normalize_text(str(data.get("subject", ""))) or f"Application for {job_title} - {profile.name}"
        body = normalize_multiline(str(data.get("body", "")))
        if not body:
            raise ValueError("Empty body returned by model.")
        return ColdEmailDraft(
            subject=subject,
            body=body,
            recruiter_email=recruiter_email,
            user_email=profile.email,
            job_description=job_description,
            job_title=job_title,
        )
    except Exception as exc:
        logging.exception("Draft generation failed, using fallback template: %s", exc)
        return build_fallback_draft(profile, recruiter_email, job_description, job_title)


def revise_cold_email_draft(
    profile: ColdEmailProfile,
    draft: ColdEmailDraft,
    feedback: str,
) -> ColdEmailDraft:
    feedback = normalize_text(feedback)
    if not feedback:
        return draft

    client = get_groq_client()
    if not client:
        return build_fallback_draft(profile, draft.recruiter_email, draft.job_description, draft.job_title)

    model = os.getenv("MODEL", "llama-3.3-70b-versatile")
    prompt = (
        "Revise the existing job application email based on user feedback.\n"
        "This is an application email, not a referral request.\n"
        "Return strict JSON only in this format:\n"
        "{\"subject\":\"...\",\"body\":\"...\"}\n"
        "Keep it professional, concise, and recruiter-friendly.\n"
        f"User feedback: {feedback}\n"
        f"Previous subject: {draft.subject}\n"
        f"Previous body:\n{draft.body}\n\n"
        f"Job title: {draft.job_title}\n"
        f"Job description:\n{draft.job_description}\n\n"
        f"Resume context:\n{build_resume_context(profile)}"
    )

    try:
        response = client.chat.completions.create(
            model=model,
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}],
        )
        data = parse_json_object(response.choices[0].message.content.strip())
        subject = normalize_text(str(data.get("subject", ""))) or draft.subject
        body = normalize_multiline(str(data.get("body", ""))) or draft.body
        return ColdEmailDraft(
            subject=subject,
            body=body,
            recruiter_email=draft.recruiter_email,
            user_email=draft.user_email,
            job_description=draft.job_description,
            job_title=draft.job_title,
        )
    except Exception as exc:
        logging.exception("Draft revision failed, keeping previous draft: %s", exc)
        return draft


def load_gmail_service() -> Any:
    creds = None
    if TOKEN_FILE.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
        except Exception:
            logging.warning("Existing cold email token is not valid JSON. Re-authentication required.")
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            cred_path = os.getenv("GMAIL_CREDENTIALS_FILE", "email_credentials.json")
            flow = InstalledAppFlow.from_client_secrets_file(cred_path, SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")

    return build("gmail", "v1", credentials=creds)


def render_email_html(body_text: str) -> str:
    lines = [line.strip() for line in normalize_multiline(body_text).splitlines()]
    html_lines = "<br>".join(line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") for line in lines)
    return f"<html><body style=\"font-family:Arial,sans-serif;line-height:1.6;\">{html_lines}</body></html>"


def build_email_message(
    to_email: str,
    subject: str,
    body_text: str,
    attachment_path: str | None = None,
) -> MIMEMultipart:
    message = MIMEMultipart("mixed")
    message["to"] = to_email
    message["subject"] = subject

    alternative = MIMEMultipart("alternative")
    alternative.attach(MIMEText(normalize_multiline(body_text), "plain", "utf-8"))
    alternative.attach(MIMEText(render_email_html(body_text), "html", "utf-8"))
    message.attach(alternative)

    if attachment_path:
        path = Path(attachment_path).expanduser().resolve()
        if path.exists():
            with path.open("rb") as file_handle:
                attachment = MIMEBase("application", "pdf")
                attachment.set_payload(file_handle.read())
            encoders.encode_base64(attachment)
            attachment.add_header("Content-Disposition", "attachment", filename=path.name)
            message.attach(attachment)

    return message


def send_email_via_gmail(
    to_email: str,
    subject: str,
    body_text: str,
    attachment_path: str | None = None,
) -> str:
    sender = os.getenv("GMAIL_SENDER", "me")
    service = load_gmail_service()
    message = build_email_message(to_email, subject, body_text, attachment_path=attachment_path)
    encoded = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    response = service.users().messages().send(userId=sender, body={"raw": encoded}).execute()
    return str(response.get("id", "unknown"))
