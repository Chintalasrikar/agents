"""
Authentication utilities that work with environment variables instead of files.
This enables secure deployment to cloud platforms like Render.
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


def create_credentials_from_env(service_type: str = "cold_email") -> Optional[Credentials]:
    """
    Create Google OAuth credentials from environment variables.
    
    Args:
        service_type: Either 'cold_email' or 'news' for different token sets
    """
    # Choose the right environment variables based on service type
    if service_type == "news":
        refresh_token = os.getenv("NEWS_GMAIL_REFRESH_TOKEN")
        access_token = os.getenv("NEWS_GMAIL_ACCESS_TOKEN") 
    else:
        refresh_token = os.getenv("GMAIL_REFRESH_TOKEN")
        access_token = os.getenv("GMAIL_ACCESS_TOKEN")
    
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    
    if not all([refresh_token, client_id, client_secret]):
        return None
        
    # Create credentials object
    creds = Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=["https://www.googleapis.com/auth/gmail.send"]
    )
    
    return creds


def get_credentials_json_from_env() -> str:
    """
    Create the credentials JSON content from environment variables.
    This replaces reading from email_credentials.json file.
    """
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET") 
    project_id = os.getenv("GOOGLE_PROJECT_ID")
    
    if not all([client_id, client_secret, project_id]):
        raise ValueError("Missing Google OAuth environment variables")
        
    credentials_data = {
        "installed": {
            "client_id": client_id,
            "project_id": project_id,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token", 
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": client_secret,
            "redirect_uris": ["http://localhost"]
        }
    }
    
    return json.dumps(credentials_data)


def load_gmail_service_from_env(service_type: str = "cold_email") -> Any:
    """
    Load Gmail service using credentials from environment variables.
    
    Args:
        service_type: Either 'cold_email' or 'news' for different token sets
    """
    creds = create_credentials_from_env(service_type)
    
    if not creds:
        # Fallback to file-based auth for local development
        token_file = "cold_email_token.json" if service_type == "cold_email" else "token.pickle"
        if Path(token_file).exists():
            try:
                creds = Credentials.from_authorized_user_file(token_file, ["https://www.googleapis.com/auth/gmail.send"])
            except Exception:
                creds = None
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                raise RuntimeError(f"Failed to refresh OAuth credentials: {e}")
        else:
            raise RuntimeError(
                f"OAuth credentials not available. Please set up environment variables or run local OAuth flow."
            )
    
    return build("gmail", "v1", credentials=creds)


def save_token_to_env_format(token_data: dict, service_type: str = "cold_email") -> str:
    """
    Helper to convert token data to environment variable format.
    This is useful when setting up tokens initially.
    """
    prefix = "NEWS_GMAIL_" if service_type == "news" else "GMAIL_"
    
    env_vars = []
    env_vars.append(f"{prefix}ACCESS_TOKEN={token_data.get('token', '')}")
    env_vars.append(f"{prefix}REFRESH_TOKEN={token_data.get('refresh_token', '')}")
    
    return "\n".join(env_vars)