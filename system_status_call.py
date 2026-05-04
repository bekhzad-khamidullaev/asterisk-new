#!/usr/bin/env python3
import configparser
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path


CONFIG_PATH = os.environ.get(
    "SYSTEM_STATUS_CONFIG",
    "/etc/asterisk/scripts/system_status_call.ini",
)

LANG_META = {
    "en": {
        "edge_voice": "en-US-GuyNeural",
        "greeting": "Hello.",
        "intro": "This is your daily system status report.",
        "time": "Report time: {time}.",
        "memory": "Available memory is {free:.1f} gigabytes out of {total:.1f}.",
        "disk": "Available disk space is {free:.1f} gigabytes out of {total:.1f}.",
        "load": "The one-minute system load is {load:.2f}.",
        "issues_intro": "Attention. I found the following issues.",
        "issues": {
            "asterisk": "Asterisk is not responding.",
            "mariadb": "The MariaDB database is not responding.",
            "odbc": "The ODBC database connection is down.",
            "turn": "The TURN service is not listening on port 3478.",
        },
        "healthy": [
            "Asterisk is healthy.",
            "The database is healthy.",
            "The ODBC connection is healthy.",
            "The TURN service is healthy.",
            "No critical issues were detected.",
        ],
    },
    "ru": {
        "edge_voice": "ru-RU-DmitryNeural",
        "greeting": "Здравствуйте.",
        "intro": "Это ежедневный отчёт о состоянии системы.",
        "time": "Время отчёта: {time}.",
        "memory": "Свободная память {free:.1f} гигабайт из {total:.1f}.",
        "disk": "Свободное место на диске {free:.1f} гигабайт из {total:.1f}.",
        "load": "Нагрузка за одну минуту {load:.2f}.",
        "issues_intro": "Внимание. Обнаружены следующие проблемы.",
        "issues": {
            "asterisk": "Астериск недоступен.",
            "mariadb": "База Мария Ди Би недоступна.",
            "odbc": "Подключение ОДИБИСИ не работает.",
            "turn": "Сервис ТЕРН не слушает порт 3478.",
        },
        "healthy": [
            "Астериск работает штатно.",
            "База данных работает штатно.",
            "ОДИБИСИ подключен.",
            "ТЕРН сервис работает штатно.",
            "Критических проблем не обнаружено.",
        ],
    },
    "uz": {
        "edge_voice": "uz-UZ-SardorNeural",
        "greeting": "Assalomu alaykum.",
        "intro": "Bu tizim holati bo'yicha kunlik hisobot.",
        "time": "Hisobot vaqti: {time}.",
        "memory": "Bo'sh xotira {free} gigabayt, umumiy xotira {total} gigabayt.",
        "disk": "Diskdagi bo'sh joy {free} gigabayt, umumiy hajm {total} gigabayt.",
        "load": "So'nggi bir daqiqadagi tizim yuklamasi {load}.",
        "issues_intro": "Diqqat. Quyidagi muammolar aniqlandi.",
        "issues": {
            "asterisk": "Asterisk javob bermayapti.",
            "mariadb": "MariaDB bazasi javob bermayapti.",
            "odbc": "ODBC ulanishi ishlamayapti.",
            "turn": "TURN xizmati 3478-portni tinglamayapti.",
        },
        "healthy": [
            "Asterisk normal ishlamoqda.",
            "Ma'lumotlar bazasi normal ishlamoqda.",
            "ODBC ulanishi faol.",
            "TURN xizmati normal ishlamoqda.",
            "Kritik muammolar aniqlanmadi.",
        ],
    },
}

UZ_DIGIT_WORDS = {
    "0": "nol",
    "1": "bir",
    "2": "ikki",
    "3": "uch",
    "4": "to'rt",
    "5": "besh",
    "6": "olti",
    "7": "yetti",
    "8": "sakkiz",
    "9": "to'qqiz",
}


def run_cmd(command):
    return subprocess.run(
        command,
        shell=True,
        text=True,
        capture_output=True,
        timeout=20,
    )


def read_config(path):
    config = configparser.ConfigParser()
    if not config.read(path):
        raise FileNotFoundError(f"Config not found: {path}")
    return config["report"]


def load_last_date(path):
    try:
        raw = Path(path).read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return {}

    if not raw:
        return {}

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        # Backward compatibility with legacy plain-text state file.
        return {"legacy": raw}

    if isinstance(parsed, dict):
        return {str(k): str(v) for k, v in parsed.items()}
    return {}


def save_last_date(path, value):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, ensure_ascii=True, sort_keys=True), encoding="utf-8")


def get_memory_status():
    total_kb = 0
    available_kb = 0
    with open("/proc/meminfo", "r", encoding="utf-8") as handle:
        for line in handle:
            if line.startswith("MemTotal:"):
                total_kb = int(line.split()[1])
            elif line.startswith("MemAvailable:"):
                available_kb = int(line.split()[1])
    return total_kb / 1024 / 1024, available_kb / 1024 / 1024


def get_load_status():
    with open("/proc/loadavg", "r", encoding="utf-8") as handle:
        parts = handle.read().strip().split()
    return float(parts[0]), float(parts[1]), float(parts[2])


def get_disk_status(path):
    total, used, free = shutil.disk_usage(path)
    return total / 1024 / 1024 / 1024, free / 1024 / 1024 / 1024


def check_asterisk():
    result = run_cmd("asterisk -rx 'core show uptime seconds'")
    return result.returncode == 0, result.stdout.strip() or result.stderr.strip()


def check_odbc():
    result = run_cmd("asterisk -rx 'odbc show all'")
    ok = result.returncode == 0 and "Name:   asterisk" in result.stdout and "active connections" in result.stdout
    return ok, result.stdout.strip() or result.stderr.strip()


def check_mariadb():
    result = run_cmd("mysql -uasterisk -pt3sl@admin -Nse 'SELECT 1' asterisk_db")
    return result.returncode == 0 and result.stdout.strip() == "1", result.stdout.strip() or result.stderr.strip()


def check_turn():
    result = run_cmd("ss -lntu | grep -E '(:3478\\s|:3478$)'")
    return result.returncode == 0, result.stdout.strip() or result.stderr.strip()


def collect_status_data():
    issues = []

    asterisk_ok, _ = check_asterisk()
    if not asterisk_ok:
        issues.append("asterisk")

    mariadb_ok, _ = check_mariadb()
    if not mariadb_ok:
        issues.append("mariadb")

    odbc_ok, _ = check_odbc()
    if not odbc_ok:
        issues.append("odbc")

    turn_ok, _ = check_turn()
    if not turn_ok:
        issues.append("turn")

    mem_total, mem_free = get_memory_status()
    disk_total, disk_free = get_disk_status("/")
    load1, _, _ = get_load_status()
    now = datetime.now()

    return {
        "issues": issues,
        "mem_total": mem_total,
        "mem_free": mem_free,
        "disk_total": disk_total,
        "disk_free": disk_free,
        "load1": load1,
        "time": now.strftime("%H:%M"),
    }


def render_report_text(language, status):
    meta = LANG_META[language]
    time_value = status["time"]
    mem_free = status["mem_free"]
    mem_total = status["mem_total"]
    disk_free = status["disk_free"]
    disk_total = status["disk_total"]
    load1 = status["load1"]

    if language == "uz":
        time_value = uz_spell_time(status["time"])
        mem_free = uz_spell_number(status["mem_free"], 1)
        mem_total = uz_spell_number(status["mem_total"], 1)
        disk_free = uz_spell_number(status["disk_free"], 1)
        disk_total = uz_spell_number(status["disk_total"], 1)
        load1 = uz_spell_number(status["load1"], 2)

    parts = [
        meta["greeting"],
        meta["intro"],
        meta["time"].format(time=time_value),
        meta["memory"].format(free=mem_free, total=mem_total),
        meta["disk"].format(free=disk_free, total=disk_total),
        meta["load"].format(load=load1),
    ]

    if status["issues"]:
        parts.append(meta["issues_intro"])
        parts.extend(meta["issues"][issue_key] for issue_key in status["issues"])
    else:
        parts.extend(meta["healthy"])

    return " ".join(parts)


def uz_spell_digits(value):
    return " ".join(UZ_DIGIT_WORDS[ch] for ch in value if ch in UZ_DIGIT_WORDS)


def uz_spell_number(value, decimals):
    rendered = f"{value:.{decimals}f}"
    out = []
    for ch in rendered:
        if ch in UZ_DIGIT_WORDS:
            out.append(UZ_DIGIT_WORDS[ch])
        elif ch == ".":
            out.append("nuqta")
    return " ".join(out)


def uz_spell_time(time_str):
    if ":" not in time_str:
        return time_str
    hh, mm = time_str.split(":", 1)
    return f"{uz_spell_digits(hh)} dan {uz_spell_digits(mm)}"


def synthesize_wav(text, wav_path, language, cache_dir):
    if not shutil.which("sox"):
        raise RuntimeError("sox is required for 8k conversion")

    meta = LANG_META.get(language, LANG_META["en"])
    voice = meta.get("edge_voice")
    if not voice:
        raise RuntimeError(f"edge voice is not configured for language: {language}")

    cache_root = Path(cache_dir)
    cache_root.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(f"{language}|{voice}|{text}".encode("utf-8")).hexdigest()
    cached_wav = cache_root / f"{digest}.wav"

    wav_file = Path(wav_path)
    wav_file.parent.mkdir(parents=True, exist_ok=True)
    if cached_wav.exists():
        shutil.copy2(cached_wav, wav_file)
        return

    with tempfile.TemporaryDirectory(prefix="sys_status_tts_") as tmpdir:
        tmp_mp3 = Path(tmpdir) / "edge.mp3"
        edge_cmd = [
            sys.executable,
            "-m",
            "edge_tts",
            "--voice",
            voice,
            "--text",
            text,
            "--write-media",
            str(tmp_mp3),
        ]
        result = subprocess.run(edge_cmd, text=True, capture_output=True, timeout=120)
        if result.returncode != 0 or not tmp_mp3.exists():
            raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "edge-tts failed")

        tmp_wav = Path(tmpdir) / "edge_8k.wav"
        conv = subprocess.run(
            ["sox", str(tmp_mp3), "-r", "8000", "-c", "1", "-b", "16", "-e", "signed-integer", str(tmp_wav)],
            text=True,
            capture_output=True,
            timeout=120,
        )
        if conv.returncode != 0 or not tmp_wav.exists():
            raise RuntimeError(conv.stderr.strip() or "sox failed")

        shutil.copy2(tmp_wav, cached_wav)
        shutil.copy2(tmp_wav, wav_file)


def parse_languages(raw_value):
    selected = []
    for item in raw_value.split(","):
        lang = item.strip().lower()
        if lang in LANG_META and lang not in selected:
            selected.append(lang)
    return selected or ["en"]


def parse_channels(section, number):
    templates = section.get("channel_templates", "").strip()
    if templates:
        return [item.strip().format(number=number) for item in templates.split(",") if item.strip()]
    return [section.get("channel_template", "PJSIP/{number}").format(number=number)]


def merge_wavs(output_wav, segments):
    if len(segments) == 1:
        shutil.move(str(segments[0]), str(output_wav))
        return

    if not shutil.which("sox"):
        raise RuntimeError("sox is required to merge multiple language audio segments")

    result = subprocess.run(
        ["sox", *[str(p) for p in segments], str(output_wav)],
        text=True,
        capture_output=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "sox merge failed")

    for segment in segments:
        segment.unlink(missing_ok=True)


def ami_command(host, port, username, secret, variables, channel, context, exten, priority, callerid, timeout_ms):
    payload_lines = [
        "Action: Login",
        f"Username: {username}",
        f"Secret: {secret}",
        "",
        "Action: Originate",
        f"Channel: {channel}",
        f"Context: {context}",
        f"Exten: {exten}",
        f"Priority: {priority}",
        f"CallerID: {callerid}",
        "Async: false",
        f"Timeout: {timeout_ms}",
    ]

    for key, value in variables.items():
        payload_lines.append(f"Variable: {key}={value}")

    payload_lines.extend(
        [
            "",
            "Action: Logoff",
            "",
        ]
    )
    payload = "\r\n".join(payload_lines)

    with socket.create_connection((host, port), timeout=10) as sock:
        sock.settimeout(2)
        sock.sendall(payload.encode("utf-8"))
        sock.shutdown(socket.SHUT_WR)
        chunks = []
        while True:
            try:
                data = sock.recv(65535)
            except TimeoutError:
                break
            if not data:
                break
            chunks.append(data)
        response = b"".join(chunks).decode("utf-8", errors="ignore")
    return response


def should_run(section, now):
    if section.get("enabled", "no").lower() != "yes":
        return False
    schedule = section.get("time", "06:00").strip()
    return now.strftime("%H:%M") == schedule


def parse_schedule_targets(section):
    raw = section.get("schedule_targets", "").strip()
    if not raw:
        return [(section.get("time", "06:00").strip(), section.get("number", "").strip())]

    items = []
    for part in raw.split(","):
        token = part.strip()
        if not token:
            continue
        if "|" in token:
            hhmm, number = token.split("|", 1)
        elif "=" in token:
            hhmm, number = token.split("=", 1)
        else:
            continue
        items.append((hhmm.strip(), number.strip()))
    return items


def resolve_target(section, now, run_now):
    targets = parse_schedule_targets(section)
    if not targets:
        return None

    if run_now:
        for hhmm, number in targets:
            if number:
                return hhmm, number
        return targets[0]

    if section.get("enabled", "no").lower() != "yes":
        return None

    current = now.strftime("%H:%M")
    for hhmm, number in targets:
        if hhmm == current:
            return hhmm, number
    return None


def main():
    run_now = "--run-now" in sys.argv
    dry_run = "--dry-run" in sys.argv

    section = read_config(CONFIG_PATH)
    state_file = section.get("state_file", "/var/lib/asterisk/sounds/system-status/.last_report_date")
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")

    target = resolve_target(section, now, run_now)
    if not target:
        return 0

    slot_time, slot_number = target
    slot_key = f"{slot_time}|{slot_number}"
    sent_state = load_last_date(state_file)
    if not run_now and sent_state.get(slot_key) == today:
        return 0

    status = collect_status_data()
    languages = parse_languages(section.get("languages", "uz,ru,en"))
    sounds_dir = section.get("sounds_dir", "/var/lib/asterisk/sounds/system-status").rstrip("/")
    cache_dir = section.get("cache_dir", f"{sounds_dir}/cache").rstrip("/")
    audio_base = f"{sounds_dir}/daily-status"
    output_wav = Path(f"{audio_base}.wav")
    generated_segments = []
    rendered_texts = []
    for language in languages:
        rendered = render_report_text(language, status)
        rendered_texts.append(f"[{language}] {rendered}")
        segment = Path(f"{audio_base}-{language}.wav")
        synthesize_wav(rendered, str(segment), language, cache_dir)
        generated_segments.append(segment)

    merge_wavs(output_wav, generated_segments)
    playback_audio = "system-status/daily-status"

    if dry_run:
        print("\n".join(rendered_texts))
        return 0

    number = slot_number
    if not number:
        print(f"number is empty in config for slot {slot_time}", file=sys.stderr)
        return 1

    channels = parse_channels(section, number)
    context = section.get("context", "system-status-call")
    exten = section.get("exten", "s")
    priority = section.get("priority", "1")
    callerid = section.get("callerid", "System Report")
    timeout_ms = section.getint("timeout_ms", 45000)
    host = section.get("ami_host", "127.0.0.1")
    port = section.getint("ami_port", 5038)
    username = section.get("ami_username", "admin")
    secret = section.get("ami_secret", "")

    delivered = False
    for channel in channels:
        response = ami_command(
            host=host,
            port=port,
            username=username,
            secret=secret,
            variables={"STATUS_AUDIO": playback_audio},
            channel=channel,
            context=context,
            exten=exten,
            priority=priority,
            callerid=callerid,
            timeout_ms=timeout_ms,
        )
        compact_response = " ".join(line.strip() for line in response.splitlines() if line.strip())
        print(f"[originate] channel={channel} response={compact_response}")
        if "Response: Success" in response and "Response: Error" not in response:
            delivered = True
            break

    if not delivered:
        return 1

    sent_state[slot_key] = today
    save_last_date(state_file, sent_state)
    print(" | ".join(rendered_texts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
