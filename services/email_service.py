"""
Email service.

Sends interview-invitation and rejection emails over SMTP. All connection
details come from environment variables so credentials never live in code:

    SMTP_HOST       default: smtp.gmail.com
    SMTP_PORT       default: 587
    SMTP_USER       required -- the mailbox that logs in and sends
    SMTP_PASSWORD   required -- app password / SMTP password
    FROM_EMAIL      default: SMTP_USER
    FROM_NAME       default: "Hiring Team"

See .env.example in the project root for a template.
"""

import os
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional


class EmailServiceError(Exception):
    """Raised when an email could not be sent (bad config, SMTP failure, etc.)."""


def _config():
    return {
        "host": os.getenv("SMTP_HOST", "smtp.gmail.com"),
        "port": int(os.getenv("SMTP_PORT", "587")),
        "user": os.getenv("SMTP_USER"),
        "password": os.getenv("SMTP_PASSWORD"),
        "from_email": os.getenv("FROM_EMAIL") or os.getenv("SMTP_USER"),
        "from_name": os.getenv("FROM_NAME", "Hiring Team"),
    }


def _send(to_email: str, subject: str, html_body: str, text_body: str) -> None:
    cfg = _config()
    if not cfg["user"] or not cfg["password"]:
        raise EmailServiceError(
            "SMTP is not configured. Set SMTP_USER and SMTP_PASSWORD "
            "(and optionally SMTP_HOST/SMTP_PORT/FROM_EMAIL/FROM_NAME) as environment variables."
        )

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = f'{cfg["from_name"]} <{cfg["from_email"]}>'
    message["To"] = to_email
    message.attach(MIMEText(text_body, "plain"))
    message.attach(MIMEText(html_body, "html"))

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(cfg["host"], cfg["port"]) as server:
            server.starttls(context=context)
            server.login(cfg["user"], cfg["password"])
            server.sendmail(cfg["from_email"], [to_email], message.as_string())
    except Exception as exc:
        raise EmailServiceError(f"Failed to send email to {to_email}: {exc}") from exc


def send_interview_email(
    to_email: str,
    candidate_name: str,
    job_title: Optional[str] = None,
    interview_datetime: Optional[str] = None,
    interview_location: Optional[str] = None,
    additional_notes: Optional[str] = None,
) -> None:
    role_phrase = f" for the {job_title} role" if job_title else ""
    subject = f"Interview Invitation{f' – {job_title}' if job_title else ''}"

    details_html = ""
    details_text = ""
    if interview_datetime:
        details_html += f"<p><strong>When:</strong> {interview_datetime}</p>"
        details_text += f"When: {interview_datetime}\n"
    if interview_location:
        details_html += f"<p><strong>Where / Link:</strong> {interview_location}</p>"
        details_text += f"Where / Link: {interview_location}\n"
    if additional_notes:
        details_html += f"<p>{additional_notes}</p>"
        details_text += f"{additional_notes}\n"

    html_body = f"""
    <div style="font-family: Arial, sans-serif; color: #222; line-height: 1.5;">
      <p>Dear {candidate_name},</p>
      <p>Thank you for applying{role_phrase}. We were impressed with your profile
         and would like to invite you to the next round -- an interview.</p>
      {details_html}
      <p>Please reply to this email to confirm your availability, or let us know
         if you need to reschedule.</p>
      <p>Looking forward to speaking with you.</p>
      <p>Best regards,<br/>{_config()["from_name"]}</p>
    </div>
    """
    text_body = (
        f"Dear {candidate_name},\n\n"
        f"Thank you for applying{role_phrase}. We were impressed with your profile "
        f"and would like to invite you to the next round -- an interview.\n\n"
        f"{details_text}\n"
        f"Please reply to this email to confirm your availability, or let us know "
        f"if you need to reschedule.\n\n"
        f"Looking forward to speaking with you.\n\n"
        f'Best regards,\n{_config()["from_name"]}'
    )

    _send(to_email, subject, html_body, text_body)


def send_rejection_email(
    to_email: str,
    candidate_name: str,
    job_title: Optional[str] = None,
    additional_notes: Optional[str] = None,
) -> None:
    role_phrase = f" for the {job_title} role" if job_title else ""
    subject = f"Update on your application{f' – {job_title}' if job_title else ''}"

    notes_html = f"<p>{additional_notes}</p>" if additional_notes else ""
    notes_text = f"{additional_notes}\n" if additional_notes else ""

    html_body = f"""
    <div style="font-family: Arial, sans-serif; color: #222; line-height: 1.5;">
      <p>Dear {candidate_name},</p>
      <p>Thank you for taking the time to apply{role_phrase} and for sharing your
         background with us. After careful review, we've decided to move forward
         with other candidates whose experience more closely matches what we
         need right now.</p>
      {notes_html}
      <p>We appreciate your interest and encourage you to apply again for future
         openings that match your profile.</p>
      <p>Wishing you the best in your job search.</p>
      <p>Best regards,<br/>{_config()["from_name"]}</p>
    </div>
    """
    text_body = (
        f"Dear {candidate_name},\n\n"
        f"Thank you for taking the time to apply{role_phrase} and for sharing your "
        f"background with us. After careful review, we've decided to move forward "
        f"with other candidates whose experience more closely matches what we need "
        f"right now.\n\n"
        f"{notes_text}\n"
        f"We appreciate your interest and encourage you to apply again for future "
        f"openings that match your profile.\n\n"
        f"Wishing you the best in your job search.\n\n"
        f'Best regards,\n{_config()["from_name"]}'
    )

    _send(to_email, subject, html_body, text_body)
