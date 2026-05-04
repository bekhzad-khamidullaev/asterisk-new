#!/usr/bin/env python3
import base64
import hashlib
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SOUNDS_SUBDIR = "zabbix-alert"
SOUNDS_ROOT = Path("/var/lib/asterisk/sounds")
SOUNDS_DIR = SOUNDS_ROOT / SOUNDS_SUBDIR
CACHE_DIR = SOUNDS_DIR / "cache"
VOICE_MAP = {
    "ru": "ru-RU-DmitryNeural",
    "uz": "uz-UZ-SardorNeural",
}
FALLBACK_TEXT = "Внимание. Обнаружена авария в системе мониторинга."


def read_agi_env():
    env = {}
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        line = line.strip()
        if not line:
            break
        if ":" in line:
            key, value = line.split(":", 1)
            env[key.strip()] = value.strip()
    return env


def agi_cmd(command):
    sys.stdout.write(f"{command}\n")
    sys.stdout.flush()
    return sys.stdin.readline().strip()


def agi_get_var(name):
    response = agi_cmd(f"GET VARIABLE {name}")
    match = re.search(r"result=(\d+)(?:\s+\((.*)\))?", response)
    if not match:
        return ""
    if match.group(1) != "1":
        return ""
    return (match.group(2) or "").strip()


def safe_b64_decode(payload):
    if not payload:
        return ""
    payload = payload.strip()
    payload += "=" * (-len(payload) % 4)
    try:
        return base64.urlsafe_b64decode(payload.encode("utf-8")).decode("utf-8", "replace")
    except Exception:
        return ""


def clean_text(text, max_chars=450):
    text = re.sub(r"\s+", " ", text or "").strip()
    text = "".join(ch for ch in text if ch.isprintable())
    if len(text) > max_chars:
        text = text[:max_chars]
    return text


def speed_to_rate(speed):
    # Map speech speed input [120..190] to edge-tts rate percentage.
    pct = int((speed - 145) * 2)
    pct = max(-50, min(80, pct))
    return f"{pct:+d}%"


def detect_voice(voice_raw):
    lang = (voice_raw or "ru").lower()
    if lang.startswith("uz"):
        return "uz", VOICE_MAP["uz"]
    return "ru", VOICE_MAP["ru"]


def cache_key(text, lang, voice, rate):
    payload = f"{lang}|{voice}|{rate}|{text}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def synthesize(text, voice_raw, speed):
    if not shutil.which("sox"):
        raise RuntimeError("sox is required for 8k conversion")

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    lang, edge_voice = detect_voice(voice_raw)
    rate = speed_to_rate(speed)
    digest = cache_key(text, lang, edge_voice, rate)
    wav_path = CACHE_DIR / f"{digest}.wav"

    if wav_path.exists():
        return wav_path

    with tempfile.TemporaryDirectory(prefix="zbx_tts_") as tmpdir:
        tmp_mp3 = Path(tmpdir) / "edge.mp3"
        edge_cmd = [
            sys.executable,
            "-m",
            "edge_tts",
            "--voice",
            edge_voice,
            "--rate",
            rate,
            "--text",
            text,
            "--write-media",
            str(tmp_mp3),
        ]
        proc = subprocess.run(edge_cmd, capture_output=True, text=True, timeout=120)
        if proc.returncode != 0 or not tmp_mp3.exists():
            raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "edge-tts failed")

        tmp_wav = Path(tmpdir) / "edge_8k.wav"
        sox_cmd = [
            "sox",
            str(tmp_mp3),
            "-r",
            "8000",
            "-c",
            "1",
            "-b",
            "16",
            "-e",
            "signed-integer",
            str(tmp_wav),
        ]
        conv = subprocess.run(sox_cmd, capture_output=True, text=True, timeout=120)
        if conv.returncode != 0 or not tmp_wav.exists():
            raise RuntimeError(conv.stderr.strip() or "sox conversion failed")

        tmp_wav.replace(wav_path)

    return wav_path


def main():
    read_agi_env()

    alert_b64 = agi_get_var("ALERT_B64")
    voice = (agi_get_var("ALERT_VOICE") or "ru").strip().lower()
    speed_raw = agi_get_var("ALERT_SPEED") or "145"
    repeat_raw = agi_get_var("ALERT_REPEAT") or "2"
    pregenerate = (agi_get_var("ALERT_PREGENERATE") or "0").strip() == "1"

    try:
        speed = int(speed_raw)
    except ValueError:
        speed = 145

    try:
        repeat = max(1, min(3, int(repeat_raw)))
    except ValueError:
        repeat = 2

    text = clean_text(safe_b64_decode(alert_b64))
    if not text:
        text = FALLBACK_TEXT

    try:
        wav_path = synthesize(text, voice, speed)
        rel = wav_path.relative_to(SOUNDS_ROOT)
        playback_name = str(rel.with_suffix(""))
        agi_cmd(f"SET VARIABLE ALERT_PLAYBACK {playback_name}")

        if pregenerate:
            return 0

        for idx in range(repeat):
            agi_cmd(f"STREAM FILE {playback_name} \"\"")
            if idx + 1 < repeat:
                agi_cmd("EXEC Wait 1")
    except Exception as exc:
        msg = str(exc).replace('"', "'").replace("\n", " ")
        agi_cmd("SET VARIABLE ALERT_PLAYBACK ")
        agi_cmd(f'VERBOSE "zabbix_tts_alert failed: {msg}" 1')

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
