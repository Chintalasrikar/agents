import base64
import os
import pickle
from email.utils import parseaddr
from typing import Optional, TypedDict

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from langchain_groq import ChatGroq
from pydantic import BaseModel

router = APIRouter(prefix="/email-agent", tags=["email-agent"])

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]


class EmailState(TypedDict):
    email_body: str
    sender: str
    subject: str
    thread_id: str
    message_id: str
    reply: str


class ReplyPreviewResponse(BaseModel):
    sender: str
    subject: str
    thread_id: str
    message_id: str
    email_body: str
    reply: str


class SendReplyRequest(BaseModel):
    sender: str
    subject: str
    thread_id: str = ""
    message_id: str = ""
    reply: str


class SendReplyResponse(BaseModel):
    status: str
    gmail_message_id: str


def gmail_authenticate():
    creds = None
    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file("email_credentials.json", SCOPES)
        creds = flow.run_local_server(port=0)
        with open("token.pickle", "wb") as token:
            pickle.dump(creds, token)

    return build("gmail", "v1", credentials=creds)


def get_llm() -> ChatGroq:
    load_dotenv()
    model_name = (os.getenv("MODEL") or "").strip()
    groq_api_key = (os.getenv("GROQ_API_KEY") or "").strip()

    if not model_name:
        raise HTTPException(status_code=500, detail="Missing MODEL in environment.")
    if not groq_api_key:
        raise HTTPException(status_code=500, detail="Missing GROQ_API_KEY in environment.")

    return ChatGroq(model=model_name, api_key=groq_api_key)


def extract_plain_text(part: dict) -> str:
    mime_type = part.get("mimeType", "")
    body_data = part.get("body", {}).get("data")

    if mime_type == "text/plain" and body_data:
        return base64.urlsafe_b64decode(body_data).decode("utf-8", errors="ignore")

    for subpart in part.get("parts", []):
        text = extract_plain_text(subpart)
        if text:
            return text
    return ""


def read_latest_email() -> Optional[EmailState]:
    service = gmail_authenticate()
    results = service.users().messages().list(userId="me", labelIds=["INBOX"], maxResults=1).execute()
    messages = results.get("messages", [])

    if not messages:
        return None

    msg = service.users().messages().get(userId="me", id=messages[0]["id"]).execute()
    payload = msg.get("payload", {})
    headers = payload.get("headers", [])

    sender = ""
    subject = ""
    message_id = ""

    for header in headers:
        name = header.get("name", "")
        value = header.get("value", "")
        if name == "From":
            sender = value
        elif name == "Subject":
            subject = value
        elif name == "Message-ID":
            message_id = value

    body = extract_plain_text(payload)

    return {
        "email_body": body,
        "sender": sender,
        "subject": subject,
        "thread_id": msg.get("threadId", ""),
        "message_id": message_id,
        "reply": "",
    }


def generate_reply(state: EmailState) -> str:
    llm = get_llm()
    sender_name = parseaddr(state.get("sender", ""))[0] or "there"
    clean_subject = state.get("subject", "").strip() or "your email"

    prompt = f"""
You are an AI email assistant.
Write a concise, natural reply to the email below.

Rules:
- Personalize using the sender name "{sender_name}" if available.
- Acknowledge the actual request/content from the email.
- Keep it short (3-6 lines).
- Do NOT include placeholders like [Sender's Name].
- Do NOT include "Subject:" or any signature block unless requested.
- Return only the reply body text.

Original subject: {clean_subject}
Original email body:
{state['email_body']}
"""

    response = llm.invoke(prompt)
    reply_text = (response.content or "").strip()
    if reply_text.lower().startswith("subject:"):
        reply_text = reply_text.split("\n", 1)[1].strip() if "\n" in reply_text else reply_text

    return reply_text


def send_reply_email(state: SendReplyRequest) -> str:
    service = gmail_authenticate()
    original_subject = state.subject.strip()

    if original_subject.lower().startswith("re:"):
        reply_subject = original_subject
    else:
        reply_subject = f"Re: {original_subject}" if original_subject else "Re: Your Email"

    headers = [
        f"To: {state.sender}",
        f"Subject: {reply_subject}",
    ]

    if state.message_id:
        headers.append(f"In-Reply-To: {state.message_id}")
        headers.append(f"References: {state.message_id}")

    message = "\n".join(headers) + f"\n\n{state.reply}\n"
    encoded_message = base64.urlsafe_b64encode(message.encode("utf-8")).decode("utf-8")

    create_message = {"raw": encoded_message}
    if state.thread_id:
        create_message["threadId"] = state.thread_id

    sent = service.users().messages().send(userId="me", body=create_message).execute()
    return sent.get("id", "")


@router.post("/reply-latest", response_model=ReplyPreviewResponse)
def reply_latest_email():
    state = read_latest_email()
    if not state:
        raise HTTPException(status_code=404, detail="No messages found in inbox.")

    reply = generate_reply(state)
    state["reply"] = reply

    return ReplyPreviewResponse(
        sender=state["sender"],
        subject=state["subject"],
        thread_id=state["thread_id"],
        message_id=state["message_id"],
        email_body=state["email_body"],
        reply=state["reply"],
    )


@router.post("/send-reply", response_model=SendReplyResponse)
def send_reply(payload: SendReplyRequest):
    message_id = send_reply_email(payload)
    return SendReplyResponse(status="sent", gmail_message_id=message_id)
