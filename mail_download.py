"""Daum 메일에서 업체 매입자료 첨부파일을 내려받는다.

config.ini의 [업체]에 등록된 주소에서 온 메일만 확인하고,
첨부파일을 받은자료/<날짜>/<업체명>/ 폴더에 저장한다.
이미 받은 메일은 수신기록.json에 남겨 두고 다시 받지 않는다.
"""

import configparser
import email
import getpass
import imaplib
import json
import re
import sys
from datetime import datetime, timedelta
from email.header import decode_header
from email.utils import parsedate_to_datetime
from pathlib import Path

BASE_DIR = Path(sys.executable if getattr(sys, "frozen", False) else __file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.ini"
SAVE_DIR = BASE_DIR / "받은자료"
HISTORY_PATH = BASE_DIR / "수신기록.json"

LOG_PATH = BASE_DIR / "실행기록.log"

IMAP_HOST = "imap.daum.net"
IMAP_PORT = 993


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
    log.write(f"\n===== mail_download {datetime.now():%Y-%m-%d %H:%M:%S} =====\n")
    log.flush()
    sys.stdout = Tee(sys.stdout, log)
    sys.stderr = Tee(sys.stderr, log)


def load_config():
    config = configparser.ConfigParser(inline_comment_prefixes=(";", "#"))
    config.optionxform = str  # 업체명 대소문자 유지
    config.read(CONFIG_PATH, encoding="utf-8")

    address = config.get("메일", "주소", fallback="").strip()
    if not address or "여기에" in address:
        sys.exit("config.ini의 [메일] 주소를 먼저 입력하세요.")

    days = config.getint("메일", "조회일수", fallback=7)
    suppliers = {name: addr.strip().lower() for name, addr in config.items("업체") if addr.strip()}
    if not suppliers:
        sys.exit("config.ini의 [업체]에 업체 메일 주소를 한 개 이상 입력하세요.")

    return address, days, suppliers


def load_history():
    if HISTORY_PATH.exists():
        return set(json.loads(HISTORY_PATH.read_text(encoding="utf-8")))
    return set()


def save_history(history):
    HISTORY_PATH.write_text(json.dumps(sorted(history), ensure_ascii=False, indent=2), encoding="utf-8")


def decode_text(value):
    if not value:
        return ""
    parts = []
    for text, charset in decode_header(value):
        if isinstance(text, bytes):
            parts.append(text.decode(charset or "utf-8", errors="replace"))
        else:
            parts.append(text)
    return "".join(parts)


def safe_filename(name):
    return re.sub(r'[\\/:*?"<>|]', "_", name).strip() or "첨부파일"


def unique_path(path):
    if not path.exists():
        return path
    for i in range(1, 1000):
        candidate = path.with_name(f"{path.stem}_{i}{path.suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"저장할 파일 이름을 정하지 못했습니다: {path}")


def save_attachments(msg, supplier):
    try:
        received = parsedate_to_datetime(msg["Date"])
    except (TypeError, ValueError):
        received = datetime.now()

    folder = SAVE_DIR / received.strftime("%Y-%m-%d") / safe_filename(supplier)
    saved = []
    for part in msg.walk():
        if part.get_content_maintype() == "multipart":
            continue
        filename = decode_text(part.get_filename())
        if not filename:
            continue
        payload = part.get_payload(decode=True)
        if payload is None:
            continue
        folder.mkdir(parents=True, exist_ok=True)
        path = unique_path(folder / safe_filename(filename))
        path.write_bytes(payload)
        saved.append(path)
    return saved


def main():
    address, days, suppliers = load_config()
    password = getpass.getpass(f"{address} 비밀번호 (입력 내용은 보이지 않습니다): ")

    history = load_history()
    since = (datetime.now() - timedelta(days=days)).strftime("%d-%b-%Y")

    print(f"{IMAP_HOST}에 접속합니다...")
    with imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT) as imap:
        try:
            imap.login(address, password)
        except imaplib.IMAP4.error as e:
            sys.exit(
                f"로그인에 실패했습니다. (서버 응답: {e})\n"
                "- 비밀번호를 확인하세요.\n"
                "- Daum 메일 환경설정에서 IMAP 사용을 켰는지 확인하세요.\n"
                "- 2단계 인증을 쓰면 앱 비밀번호를 입력해야 합니다."
            )
        imap.select("INBOX", readonly=True)  # 읽음 표시를 바꾸지 않는다

        total_files = 0
        for supplier, sender in suppliers.items():
            status, data = imap.search(None, "SINCE", since, "FROM", f'"{sender}"')
            if status != "OK":
                print(f"[{supplier}] 메일 검색 실패")
                continue

            ids = data[0].split()
            new_count = 0
            for num in ids:
                status, msg_data = imap.fetch(num, "(BODY.PEEK[])")
                if status != "OK":
                    continue
                msg = email.message_from_bytes(msg_data[0][1])
                message_id = msg.get("Message-ID") or f"{sender}|{msg.get('Date')}|{msg.get('Subject')}"
                if message_id in history:
                    continue

                saved = save_attachments(msg, supplier)
                history.add(message_id)
                new_count += 1
                total_files += len(saved)
                subject = decode_text(msg.get("Subject"))
                print(f"[{supplier}] {subject} - 첨부 {len(saved)}개 저장")
                for path in saved:
                    print(f"    {path.relative_to(BASE_DIR)}")

            if new_count == 0:
                print(f"[{supplier}] 새 메일 없음")

    save_history(history)
    print(f"\n완료: 첨부파일 {total_files}개 저장 ({SAVE_DIR})")


if __name__ == "__main__":
    start_log()
    try:
        main()
    finally:
        if getattr(sys, "frozen", False):
            input("\n엔터를 누르면 창이 닫힙니다.")
