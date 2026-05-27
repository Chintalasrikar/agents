import base64
import os
import pickle
from email.utils import parseaddr
from typing import Literal, Optional, TypedDict

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from langchain_groq import ChatGroq
from langgraph.graph import END, StateGraph
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
    auto_send: bool
    sent: bool
    send_status: str
    gmail_message_id: str


class RunAgentRequest(BaseModel):
    auto_send: bool = False


class AgentRunResponse(BaseModel):
    sender: str
    subject: str
    thread_id: str
    message_id: str
    email_body: str
    reply: str
    sent: bool
    send_status: str
    gmail_message_id: str


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


def read_latest_email_node(state: EmailState):
    service = gmail_authenticate()
    results = service.users().messages().list(userId="me", labelIds=["INBOX"], maxResults=1).execute()
    messages = results.get("messages", [])

    if not messages:
        raise HTTPException(status_code=404, detail="No messages found in inbox.")

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
        "sent": False,
        "send_status": "not_sent",
        "gmail_message_id": "",
    }


def generate_reply_node(state: EmailState):
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
{state.get('email_body', '')}
"""

    response = llm.invoke(prompt)
    reply_text = (response.content or "").strip()
    if reply_text.lower().startswith("subject:"):
        reply_text = reply_text.split("\n", 1)[1].strip() if "\n" in reply_text else reply_text

    return {"reply": reply_text}


def send_reply_email(sender: str, subject: str, thread_id: str, message_id: str, reply: str) -> str:
    service = gmail_authenticate()
    original_subject = subject.strip()
    reply_subject = original_subject if original_subject.lower().startswith("re:") else f"Re: {original_subject}" if original_subject else "Re: Your Email"

    headers = [
        f"To: {sender}",
        f"Subject: {reply_subject}",
    ]

    if message_id:
        headers.append(f"In-Reply-To: {message_id}")
        headers.append(f"References: {message_id}")

    message = "\n".join(headers) + f"\n\n{reply}\n"
    encoded_message = base64.urlsafe_b64encode(message.encode("utf-8")).decode("utf-8")

    create_message = {"raw": encoded_message}
    if thread_id:
        create_message["threadId"] = thread_id

    sent = service.users().messages().send(userId="me", body=create_message).execute()
    return sent.get("id", "")


def send_reply_node(state: EmailState):
    message_id = send_reply_email(
        sender=state.get("sender", ""),
        subject=state.get("subject", ""),
        thread_id=state.get("thread_id", ""),
        message_id=state.get("message_id", ""),
        reply=state.get("reply", ""),
    )
    return {"sent": True, "send_status": "sent", "gmail_message_id": message_id}


def route_after_generate(state: EmailState) -> Literal["send_reply", END]:
    return "send_reply" if state.get("auto_send") else END


workflow = StateGraph(EmailState)
workflow.add_node("read_latest_email", read_latest_email_node)
workflow.add_node("generate_reply", generate_reply_node)
workflow.add_node("send_reply", send_reply_node)
workflow.set_entry_point("read_latest_email")
workflow.add_edge("read_latest_email", "generate_reply")
workflow.add_conditional_edges("generate_reply", route_after_generate)
workflow.add_edge("send_reply", END)
agent_graph = workflow.compile()


@router.post("/run", response_model=AgentRunResponse)
def run_agent(payload: RunAgentRequest):
    result = agent_graph.invoke(
        {
            "email_body": "",
            "sender": "",
            "subject": "",
            "thread_id": "",
            "message_id": "",
            "reply": "",
            "auto_send": payload.auto_send,
            "sent": False,
            "send_status": "not_sent",
            "gmail_message_id": "",
        }
    )
    return AgentRunResponse(**result)


@router.post("/reply-latest", response_model=AgentRunResponse)
def reply_latest_email():
    result = agent_graph.invoke(
        {
            "email_body": "",
            "sender": "",
            "subject": "",
            "thread_id": "",
            "message_id": "",
            "reply": "",
            "auto_send": False,
            "sent": False,
            "send_status": "not_sent",
            "gmail_message_id": "",
        }
    )
    return AgentRunResponse(**result)


@router.post("/send-reply", response_model=SendReplyResponse)
def send_reply(payload: SendReplyRequest):
    message_id = send_reply_email(
        sender=payload.sender,
        subject=payload.subject,
        thread_id=payload.thread_id,
        message_id=payload.message_id,
        reply=payload.reply,
    )
    return SendReplyResponse(status="sent", gmail_message_id=message_id)
