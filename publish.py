#!/usr/bin/env python3
"""
Innovative Hype — Stage 3: Newsletter Publishing
================================================
Reads newsletter.md and publishes it to Substack via substack-py.

Usage:
    python3 publish.py newsletter.md
    python3 publish.py newsletter.md --config config.local.yaml
"""

import json
import sys
import os
from pathlib import Path
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

print(f"DEBUG: sys.path: {sys.path}")

# Substack-py might not be installed, handle gracefully
try:
    from substack import Api
    from substack.exceptions import SubstackAPIException
except ImportError as e:
    print(f"ERROR: python-substack library not found ({e}). Install with: pip install python-substack --target=/Users/micah/.hermes/hermes-agent/venv/lib/python3.11/site-packages")
    sys.exit(1)

def load_config(config_path="config.yaml"):
    """Load YAML config. Falls back to json if PyYAML is unavailable."""
    path = Path(config_path)
    if not path.exists():
        print(f"ERROR: Config file not found: {config_path}")
        print("Copy config.yaml to config.local.yaml and fill in your settings.")
        sys.exit(1)

    # Try YAML first
    try:
        import yaml
        with open(path) as f:
            return yaml.safe_load(f)
    except ImportError:
        pass

    # Fallback: load as JSON (we ship config.yaml in YAML format, but this
    # handles the case where someone converted it)
    try:
        with open(path) as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"ERROR: Cannot parse {config_path} — is it valid YAML/JSON?")
        sys.exit(1)


def send_email_publish(config, newsletter_content):
    """Publishes newsletter via email to Substack's posting address."""
    substack_cfg = config.get("substack", {})
    posting_address = substack_cfg.get("posting_address")

    smtp_cfg = config.get("smtp", {})
    smtp_host = smtp_cfg.get("host")
    smtp_port = smtp_cfg.get("port")
    smtp_username = smtp_cfg.get("username")
    smtp_password = smtp_cfg.get("password")

    if not all([posting_address, smtp_host, smtp_port, smtp_username, smtp_password]):
        print("ERROR: Missing SMTP or Substack posting address configuration.")
        print("Please check config.local.yaml for 'substack.posting_address' and 'smtp.*' settings.")
        return False

    msg = MIMEMultipart("alternative")
    msg["From"] = f"{smtp_username}"
    msg["To"] = posting_address
    msg["Subject"] = newsletter_content.splitlines()[0].replace("#", "").strip() # Use first line as subject

    # Attach the newsletter content as plain text and HTML
    part1 = MIMEText(newsletter_content, "plain")
    part2 = MIMEText(f"<html><body><pre>{newsletter_content}</pre></body></html>", "html")
    msg.attach(part1)
    msg.attach(part2)

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.sendmail(smtp_username, posting_address, msg.as_string())
        print(f"✅ Newsletter sent to Substack via email: {posting_address}")
        return True
    except Exception as e:
        print(f"ERROR: Failed to send email to Substack: {e}")
        print("Please check your SMTP settings (username, password, host, port) in config.local.yaml.")
        return False

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Publish newsletter to Substack"
    )
    parser.add_argument("newsletter_file", help="Path to the newsletter Markdown file")
    parser.add_argument("--config", default="config.yaml", help="Config file path")
    args = parser.parse_args()

    config = load_config(args.config)
    newsletter_path = Path(args.newsletter_file)

    if not newsletter_path.exists():
        print(f"ERROR: Newsletter file not found: {args.newsletter_file}")
        sys.exit(1)

    with open(newsletter_path, "r") as f:
        newsletter_content = f.read()

    if not newsletter_content.strip():
        print("ERROR: Newsletter content is empty. Nothing to publish.")
        sys.exit(1)

    # --- Attempt to publish via substack-py API first (more robust) ---
    substack_email = config.get("substack", {}).get("email")
    substack_password = config.get("substack", {}).get("password")
    substack_pub_id = config.get("substack", {}).get("publication_id")
    if substack_email and substack_password:
        print("Attempting to publish via python-substack API...")
        try:
            substack = Api(email=substack_email, password=substack_password)
            
            # Extract title from markdown file (first line without '#')
            title = newsletter_content.splitlines()[0].replace("#", "").strip()
            
            # publication_id is optional, if not provided, the API might infer from credentials
            post_data = {
                "title": title,
                "body": newsletter_content,
                "is_draft": True # Always create as draft first
            }
            if substack_pub_id and substack_pub_id != "optional_publication_id":
                post_data["publication_id"] = substack_pub_id

            print(f"Creating draft post with title: {title}")
            draft_post = substack.post_draft(**post_data)
            print(f"✅ Draft created successfully: {draft_post.get('edit_url') or draft_post.get('url')}")

            # Now publish the draft
            print(f"Publishing draft post ID: {draft_post.get('id')}")
            published_post = substack.publish_draft(draft_post["id"]) # or use draft_post.id
            if published_post.get("status") == "published" or published_post.get("published"):
                print(f"✅ Newsletter published successfully: {published_post.get('url')}")
            else:
                print(f"WARNING: Draft created but failed to publish via API. Check Substack dashboard.")
                print(f"Details: {published_post}")

        except SubstackAPIException as e:
            print(f"ERROR: Substack API error: {e}")
            if "Incorrect username or password" in str(e) or "invalid_grant" in str(e):
                print("Authentication failed. Please update 'substack.email' and 'substack.password' in config.local.yaml.")
            elif "publication_id" in str(e):
                print("Publication ID might be incorrect or missing. Check 'substack.publication_id' in config.local.yaml.")
            print("Falling back to email publishing.")
            send_email_publish(config, newsletter_content)
    else:
        print("Substack API credentials (email/password) not found in config.local.yaml.")
        print("Falling back to email publishing.")
        send_email_publish(config, newsletter_content)


if __name__ == "__main__":
    main()
