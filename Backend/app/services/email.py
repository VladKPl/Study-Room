import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formataddr


@dataclass(frozen=True)
class SMTPSettings:
    host: str
    port: int = 587
    username: str | None = None
    password: str | None = None
    from_email: str = ""
    from_name: str | None = None
    starttls: bool = True
    use_ssl: bool = False
    timeout_seconds: float = 10.0


def _send_via_client(client: smtplib.SMTP, message: EmailMessage, settings: SMTPSettings) -> None:
    if settings.username:
        client.login(settings.username, settings.password or "")
    client.send_message(message)


def send_password_reset_email(*, to_email: str, reset_url: str, settings: SMTPSettings) -> None:
    message = EmailMessage()
    message["Subject"] = "Study-Room: Password reset"
    if settings.from_name:
        message["From"] = formataddr((settings.from_name, settings.from_email))
    else:
        message["From"] = settings.from_email
    message["To"] = to_email
    message.set_content(
        "We received a password reset request for your Study-Room account.\n\n"
        f"Open this link to set a new password:\n{reset_url}\n\n"
        "If you did not request a password reset, just ignore this message."
    )

    if settings.use_ssl:
        with smtplib.SMTP_SSL(
            settings.host,
            settings.port,
            timeout=settings.timeout_seconds,
        ) as client:
            _send_via_client(client, message, settings)
        return

    with smtplib.SMTP(settings.host, settings.port, timeout=settings.timeout_seconds) as client:
        client.ehlo()
        if settings.starttls:
            client.starttls()
            client.ehlo()
        _send_via_client(client, message, settings)
