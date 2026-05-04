#!/usr/bin/env python3
import base64
import hashlib
import re
import socket
import sys
import time
from pathlib import Path
from typing import Dict, List

USAGE = (
    "Usage: zbxAsteriskCall.py <to> <subject> <message> <event_value> "
    "<ami_host> <ami_port> <ami_user> <ami_secret> <channel_template> "
    "<context> <exten> <priority> <callerid> <timeout_ms> "
    "[only_problem=1] [voice=ru] [speed=145] [max_chars=450] "
    "[event_id={EVENT.ID}] [dedupe_ttl_sec=900] [text_mode=summary] [repeat=2]"
)

DEFAULT_FAST_TEXT = "Внимание. Обнаружена авария в системе мониторинга."
DEDUP_DIR = Path("/tmp/zbx_asterisk_voice")
SEVERITY_MAP_RU = {
    "not classified": "не классифицировано",
    "information": "информационная",
    "warning": "предупреждение",
    "average": "средняя",
    "high": "высокая",
    "disaster": "критическая"
}


def normalize_text(text: str) -> str:
    text = re.sub(r"<[^>]*>", " ", text or "")
    text = re.sub(r"\s+", " ", text).strip()
    return "".join(ch for ch in text if ch.isprintable())


def normalize_address_terms(text: str) -> str:
    if not text:
        return text
    # "ul" -> "улица"
    text = re.sub(r"\bul\.?\s*", "улица ", text, flags=re.IGNORECASE)
    # "d-27" -> "27 дом"
    text = re.sub(r"\bd-([0-9]+)\b", r"\1 дом", text, flags=re.IGNORECASE)
    return text


def normalize_severity_words(text: str) -> str:
    if not text:
        return text

    def repl(match: re.Match) -> str:
        original = match.group(0)
        translated = SEVERITY_MAP_RU.get(original.lower())
        return translated if translated else original

    return re.sub(
        r"\b(Not classified|Information|Warning|Average|High|Disaster)\b",
        repl,
        text,
        flags=re.IGNORECASE
    )


def b64_urlsafe(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode("utf-8")).decode("ascii").rstrip("=")


def parse_recipients(raw: str) -> List[str]:
    if not raw:
        return []
    parts = [p.strip() for p in re.split(r"[;,\s]+", raw) if p.strip()]
    out = []
    for part in parts:
        cleaned = re.sub(r"[^0-9+]", "", part)
        if cleaned:
            out.append(cleaned)
    # keep order, remove duplicates
    uniq = []
    seen = set()
    for item in out:
        if item in seen:
            continue
        seen.add(item)
        uniq.append(item)
    return uniq


def parse_event_id(raw_event_id: str, subject: str, message: str) -> str:
    raw = (raw_event_id or "").strip()
    if raw.isdigit():
        return raw
    digest = hashlib.sha256(f"{subject}|{message}".encode("utf-8")).hexdigest()[:16]
    return f"hash-{digest}"


def dedupe_marker_path(event_id: str, phone: str, event_value: str) -> Path:
    key = hashlib.sha256(f"{event_id}|{phone}|{event_value}".encode("utf-8")).hexdigest()
    return DEDUP_DIR / f"{key}.mark"


def should_skip_by_dedupe(event_id: str, phone: str, event_value: str, ttl_sec: int) -> bool:
    DEDUP_DIR.mkdir(parents=True, exist_ok=True)
    marker = dedupe_marker_path(event_id, phone, event_value)
    now = time.time()

    if marker.exists():
        age = now - marker.stat().st_mtime
        if age < ttl_sec:
            return True

    return False


def mark_dedupe(event_id: str, phone: str, event_value: str) -> None:
    DEDUP_DIR.mkdir(parents=True, exist_ok=True)
    marker = dedupe_marker_path(event_id, phone, event_value)
    marker.touch()


def build_alert_text(subject: str, message: str, event_value: str, max_chars: int, mode: str) -> str:
    mode = (mode or "summary").lower()
    subject = normalize_address_terms(normalize_text(subject))
    message = normalize_address_terms(normalize_text(message))
    message = normalize_severity_words(message)

    if mode == "fast":
        text = DEFAULT_FAST_TEXT
    elif mode == "subject":
        text = subject or DEFAULT_FAST_TEXT
    else:
        pieces = []
        if event_value == "RECOVERY":
            pieces.append("Внимание. Восстановление сервиса.")
        else:
            pieces.append("Внимание. Обнаружена авария.")

        if subject:
            pieces.append(subject)

        if message:
            pieces.append(message)

        text = " ".join(pieces)

    if len(text) > max_chars:
        text = text[:max_chars].rstrip()
    return text or DEFAULT_FAST_TEXT


def parse_ami_block(raw: str) -> Dict[str, str]:
    block: Dict[str, str] = {}
    for text in raw.splitlines():
        text = text.strip()
        if not text:
            continue
        if ":" in text:
            key, value = text.split(":", 1)
            block[key.strip()] = value.strip()
    return block


def read_ami_block(sock: socket.socket, timeout_sec: int = 5) -> Dict[str, str]:
    sock.settimeout(timeout_sec)
    data = sock.recv(8192)
    if not data:
        return {}
    raw = data.decode("utf-8", "replace")
    return parse_ami_block(raw)


def send_ami_action(sock: socket.socket, action_lines: List[str]) -> Dict[str, str]:
    payload = ("\r\n".join(action_lines) + "\r\n\r\n").encode("utf-8")
    sock.sendall(payload)
    return read_ami_block(sock)


def originate_call(
    host: str,
    port: int,
    username: str,
    secret: str,
    channel_template: str,
    phone: str,
    context: str,
    exten: str,
    priority: str,
    callerid: str,
    timeout_ms: int,
    text: str,
    voice: str,
    speed: str,
    event_id: str,
    repeat: str,
) -> None:
    channel = channel_template.format(number=phone)
    action_id = hashlib.sha1(f"{event_id}|{phone}|{time.time()}".encode("utf-8")).hexdigest()[:12]

    with socket.create_connection((host, port), timeout=10) as sock:
        # AMI banner may arrive as a single line without an empty separator block.
        sock.settimeout(5)
        _ = sock.recv(4096)

        login = send_ami_action(
            sock,
            [
                "Action: Login",
                f"Username: {username}",
                f"Secret: {secret}",
                f"ActionID: login-{action_id}",
                "Events: off",
            ],
        )
        if login.get("Response") != "Success":
            raise RuntimeError(f"AMI login failed: {login}")

        alert_b64 = b64_urlsafe(text)
        originate = send_ami_action(
            sock,
            [
                "Action: Originate",
                f"ActionID: orig-{action_id}",
                f"Channel: {channel}",
                f"Context: {context}",
                f"Exten: {exten}",
                f"Priority: {priority}",
                f"CallerID: {callerid}",
                f"Timeout: {timeout_ms}",
                "Async: true",
                f"Variable: ALERT_B64={alert_b64}",
                f"Variable: ALERT_VOICE={voice}",
                f"Variable: ALERT_SPEED={speed}",
                f"Variable: ALERT_EVENTID={event_id}",
                f"Variable: ALERT_REPEAT={repeat}",
                f"Variable: ALERT_PHONE={phone}",
            ],
        )
        if originate.get("Response") != "Success":
            raise RuntimeError(f"AMI originate failed: {originate}")

        send_ami_action(
            sock,
            [
                "Action: Logoff",
                f"ActionID: logoff-{action_id}",
            ],
        )


def main() -> int:
    if len(sys.argv) < 15:
        print(USAGE, file=sys.stderr)
        return 1

    to = sys.argv[1].strip()
    subject = sys.argv[2]
    message = sys.argv[3]
    event_value = (sys.argv[4] or "").strip().upper()
    if not event_value or event_value.startswith("{"):
        event_value = "PROBLEM"
    ami_host = sys.argv[5].strip()
    ami_port = int(sys.argv[6])
    ami_user = sys.argv[7].strip()
    ami_secret = sys.argv[8].strip()
    channel_template = sys.argv[9].strip()
    context = sys.argv[10].strip()
    exten = sys.argv[11].strip()
    priority = sys.argv[12].strip()
    callerid = sys.argv[13].strip()
    timeout_ms = int(sys.argv[14])

    only_problem = (sys.argv[15].strip() if len(sys.argv) > 15 else "1")
    voice = (sys.argv[16].strip().lower() if len(sys.argv) > 16 else "ru")
    voice = "uz" if voice.startswith("uz") else "ru"
    speed = (sys.argv[17].strip() if len(sys.argv) > 17 else "145")
    try:
        max_chars = int(sys.argv[18]) if len(sys.argv) > 18 else 450
    except ValueError:
        max_chars = 450
    event_id_raw = sys.argv[19] if len(sys.argv) > 19 else "0"
    try:
        dedupe_ttl_sec = int(sys.argv[20]) if len(sys.argv) > 20 else 900
    except ValueError:
        dedupe_ttl_sec = 900
    text_mode = sys.argv[21].strip().lower() if len(sys.argv) > 21 else "summary"
    repeat = sys.argv[22].strip() if len(sys.argv) > 22 else "2"

    if only_problem == "1" and event_value != "PROBLEM":
        print("Skip: event is not PROBLEM")
        return 0

    recipients = parse_recipients(to)
    if not recipients:
        print("Error: destination number is empty", file=sys.stderr)
        return 1

    event_id = parse_event_id(event_id_raw, subject, message)
    alert_text = build_alert_text(subject, message, event_value, max_chars, text_mode)

    errors = []
    made_calls = 0
    skipped_dedup = 0

    for phone in recipients:
        if dedupe_ttl_sec > 0 and should_skip_by_dedupe(event_id, phone, event_value, dedupe_ttl_sec):
            skipped_dedup += 1
            continue

        try:
            originate_call(
                host=ami_host,
                port=ami_port,
                username=ami_user,
                secret=ami_secret,
                channel_template=channel_template,
                phone=phone,
                context=context,
                exten=exten,
                priority=priority,
                callerid=callerid,
                timeout_ms=timeout_ms,
                text=alert_text,
                voice=voice,
                speed=speed,
                event_id=event_id,
                repeat=repeat,
            )
            made_calls += 1
            if dedupe_ttl_sec > 0:
                mark_dedupe(event_id, phone, event_value)
        except Exception as exc:
            errors.append(f"{phone}: {exc}")

    if made_calls == 0 and errors:
        print("AMI originate failed for all recipients", file=sys.stderr)
        for item in errors:
            print(f" - {item}", file=sys.stderr)
        return 1

    print(
        f"OK: calls={made_calls}, dedupe_skipped={skipped_dedup}, errors={len(errors)}, event_id={event_id}"
    )
    if errors:
        for item in errors:
            print(f"WARN: {item}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
