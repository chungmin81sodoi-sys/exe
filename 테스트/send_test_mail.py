"""테스트용 거래처원장 PDF를 테스트 메일 주소로 보낸다.

보내는 주소와 받는 주소가 같다 (gsfood12@daum.net → gsfood12@daum.net).
비밀번호는 실행할 때 입력받고 저장하지 않는다.
"""

import getpass
import smtplib
import sys
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path

SMTP_HOST = "smtp.daum.net"
SMTP_PORT = 465
ADDRESS = "gsfood12@daum.net"
PDF_PATH = Path(__file__).resolve().parent / "테스트_한빛식자재_9월거래처원장.pdf"
LOG_PATH = Path(__file__).resolve().parent.parent / "실행기록.log"


class Tee:
    """화면 출력을 실행기록.log에도 남긴다. 비밀번호 입력은 getpass라 기록되지 않는다."""

    def __init__(self, stream, log):
        self.stream, self.log = stream, log

    def write(self, text):
        self.stream.write(text)
        self.log.write(text)
        self.log.flush()

    def flush(self):
        self.stream.flush()


def start_log():
    log = open(LOG_PATH, "a", encoding="utf-8")
    log.write(f"\n===== send_test_mail {datetime.now():%Y-%m-%d %H:%M:%S} =====\n")
    log.flush()
    sys.stdout = Tee(sys.stdout, log)
    sys.stderr = Tee(sys.stderr, log)


def main():
    if not PDF_PATH.exists():
        sys.exit(f"테스트 PDF가 없습니다. make_test_pdf.py를 먼저 실행하세요.\n{PDF_PATH}")

    msg = EmailMessage()
    msg["From"] = ADDRESS
    msg["To"] = ADDRESS
    msg["Subject"] = "[테스트] (테스트)한빛식자재 9월 거래처원장"
    msg.set_content(
        "매입자료 자동 수신 테스트용 메일입니다.\n"
        "첨부한 거래처원장은 가상 업체의 테스트 자료이며 실제 거래가 아닙니다.\n"
    )
    msg.add_attachment(
        PDF_PATH.read_bytes(), maintype="application", subtype="pdf", filename=PDF_PATH.name
    )

    password = getpass.getpass(f"{ADDRESS} 비밀번호 (입력 내용은 보이지 않습니다): ")
    print(f"{SMTP_HOST}로 보내는 중...")
    try:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as smtp:
            smtp.login(ADDRESS, password)
            smtp.send_message(msg)
    except smtplib.SMTPAuthenticationError as e:
        reason = e.smtp_error.decode("utf-8", errors="replace") if isinstance(e.smtp_error, bytes) else str(e.smtp_error)
        sys.exit(
            f"로그인에 실패했습니다. (서버 응답 {e.smtp_code}: {reason})\n"
            "- 비밀번호를 확인하세요.\n"
            "- Daum 메일 환경설정에서 IMAP/SMTP 사용을 켰는지 확인하세요.\n"
            "- 2단계 인증을 쓰면 앱 비밀번호를 입력해야 합니다."
        )
    print(f"보냈습니다: {ADDRESS} ← {PDF_PATH.name}")


if __name__ == "__main__":
    start_log()
    main()
