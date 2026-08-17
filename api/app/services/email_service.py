"""邮箱投递服务：支持 smtp / mailhog / mock 三种模式。"""
import logging
import smtplib
import uuid
from email.header import Header
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """发送求职投递邮件。mode 由 .env 的 MAIL_MODE 决定。"""

    def __init__(self) -> None:
        self.mode = settings.MAIL_MODE
        self.host = settings.SMTP_HOST
        self.port = settings.SMTP_PORT
        self.user = settings.SMTP_USER
        self.password = settings.SMTP_PASSWORD
        self.from_addr = settings.SMTP_FROM or self.user
        self.from_name = settings.SMTP_FROM_NAME

    def _build_message(
        self,
        to_addr: str,
        subject: str,
        body_html: str,
        attachments: list[tuple[str, bytes]] | None = None,
    ) -> MIMEMultipart:
        msg = MIMEMultipart()
        msg["From"] = formataddr((str(Header(self.from_name, "utf-8")), self.from_addr))
        msg["To"] = to_addr
        msg["Subject"] = Header(subject, "utf-8")
        msg.attach(MIMEText(body_html, "html", "utf-8"))
        for filename, content in attachments or []:
            part = MIMEApplication(content)
            part.add_header("Content-Disposition", "attachment", filename=("utf-8", "", filename))
            msg.attach(part)
        return msg

    def send(
        self,
        to_addr: str,
        subject: str,
        body_html: str,
        attachments: list[tuple[str, bytes]] | None = None,
    ) -> tuple[bool, str, str]:
        """发送邮件。返回 (是否成功, message_id, 错误信息)。"""
        message_id = f"<jobflow-{uuid.uuid4().hex}@local>"
        if self.mode == "mock":
            logger.info("[mock mail] to=%s subject=%s", to_addr, subject)
            return True, message_id, ""

        # smtp 与 mailhog 均走 SMTP 协议
        host, port = self.host, self.port
        if self.mode == "mailhog":
            host, port = "127.0.0.1", 1025

        if not (host and self.user and self.password):
            logger.warning("SMTP 未配置，邮件投递降级为 mock")
            return True, message_id, ""

        msg = self._build_message(to_addr, subject, body_html, attachments)
        msg["Message-ID"] = message_id
        try:
            if port == 465:
                with smtplib.SMTP_SSL(host, port, timeout=15) as server:
                    server.login(self.user, self.password)
                    server.sendmail(self.from_addr, [to_addr], msg.as_string())
            else:
                with smtplib.SMTP(host, port, timeout=15) as server:
                    server.starttls()
                    server.login(self.user, self.password)
                    server.sendmail(self.from_addr, [to_addr], msg.as_string())
            logger.info("mail sent ok -> %s (%s)", to_addr, message_id)
            return True, message_id, ""
        except Exception as exc:  # noqa: BLE001
            logger.error("mail send failed -> %s: %s", to_addr, exc)
            return False, message_id, str(exc)


email_service = EmailService()
