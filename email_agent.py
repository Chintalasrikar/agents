from typing import TypedDict
from langgraph.graph import StateGraph, END
from email.utils import parseaddr


from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from langchain_groq import ChatGroq
from dotenv import load_dotenv

import os
import pickle
import base64

# -----------------------------
# Gmail Authentication
# -----------------------------

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify"
]

def gmail_authenticate():
    creds = None

    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(
            "email_credentials.json",
            SCOPES
        )

        creds = flow.run_local_server(port=0)

        with open("token.pickle", "wb") as token:
            pickle.dump(creds, token)

    return build("gmail", "v1", credentials=creds)

# -----------------------------
# LangGraph State
# -----------------------------

class EmailState(TypedDict):
    email_body: str
    sender: str
    subject: str
    thread_id: str
    message_id: str
    reply: str

# -----------------------------
# Read Email Tool
# -----------------------------

def read_latest_email(state):
    service = gmail_authenticate()

    results = service.users().messages().list(
        userId='me',
        labelIds=['INBOX'],
        maxResults=1
    ).execute()

    messages = results.get('messages', [])

    if not messages:
        print("No messages found.")
        return state

    msg = service.users().messages().get(
        userId='me',
        id=messages[0]['id']
    ).execute()

    payload = msg['payload']
    headers = payload['headers']

    sender = ""
    subject = ""
    message_id = ""

    for h in headers:
        if h['name'] == 'From':
            sender = h['value']
        if h['name'] == 'Subject':
            subject = h['value']
        if h['name'] == 'Message-ID':
            message_id = h['value']

    def extract_plain_text(part):
        mime_type = part.get("mimeType", "")
        body_data = part.get("body", {}).get("data")

        if mime_type == "text/plain" and body_data:
            return base64.urlsafe_b64decode(body_data).decode("utf-8", errors="ignore")

        for subpart in part.get("parts", []):
            text = extract_plain_text(subpart)
            if text:
                return text
        return ""

    body = extract_plain_text(payload)

    print("\\nEMAIL RECEIVED:")
    print(body)

    return {
        "email_body": body,
        "sender": sender,
        "subject": subject,
        "thread_id": msg.get("threadId", ""),
        "message_id": message_id
    }

# -----------------------------
# AI Reply Generator
# -----------------------------

load_dotenv()

model_name = (os.getenv("MODEL") or "").strip()
groq_api_key = (os.getenv("GROQ_API_KEY") or "").strip()

if not model_name:
    raise ValueError(
        "Missing MODEL in environment. Add MODEL to .env, e.g. MODEL=llama-3.3-70b-versatile"
    )

if not groq_api_key:
    raise ValueError("Missing GROQ_API_KEY in environment. Add it to .env.")

llm = ChatGroq(model=model_name, api_key=groq_api_key)

def generate_reply(state):
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

    print("\\nAI REPLY:")
    print(reply_text)

    return {
        "reply": reply_text
    }

# -----------------------------
# Send Email Tool
# -----------------------------

def send_reply(state):
    print("\n==============================")
    print("AI GENERATED REPLY:")
    print("==============================\n")

    print(state["reply"])

    print("\n==============================")

    approval = input("Send this reply? (y/n): ")

    if approval.lower() != "y":
        print("\nEmail sending cancelled.")
        return state

    service = gmail_authenticate()

    original_subject = state.get("subject", "").strip()
    if original_subject.lower().startswith("re:"):
        reply_subject = original_subject
    else:
        reply_subject = f"Re: {original_subject}" if original_subject else "Re: Your Email"

    headers = [
        f"To: {state['sender']}",
        f"Subject: {reply_subject}",
    ]

    if state.get("message_id"):
        headers.append(f"In-Reply-To: {state['message_id']}")
        headers.append(f"References: {state['message_id']}")

    message = "\n".join(headers) + f"\n\n{state['reply']}\n"


    encoded_message = base64.urlsafe_b64encode(
        message.encode("utf-8")
    ).decode("utf-8")

    create_message = {'raw': encoded_message}
    if state.get("thread_id"):
        create_message["threadId"] = state["thread_id"]

    send_message = service.users().messages().send(
        userId="me",
        body=create_message
    ).execute()

    print("\nEMAIL SENT SUCCESSFULLY!")

    return state

# -----------------------------
# LangGraph Workflow
# -----------------------------

workflow = StateGraph(EmailState)

workflow.add_node("read_email", read_latest_email)
workflow.add_node("generate_reply", generate_reply)
workflow.add_node("send_reply", send_reply)

workflow.set_entry_point("read_email")

workflow.add_edge("read_email", "generate_reply")
workflow.add_edge("generate_reply", "send_reply")
workflow.add_edge("send_reply", END)

app = workflow.compile()

# -----------------------------
# Run Agent
# -----------------------------

app.invoke({})
