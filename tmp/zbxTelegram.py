#!/usr/lib/zabbix/alertscripts/.venv/bin/python
# -*- coding: utf-8 -*-
########################
#    Sokolov Dmitry    #
# xx.sokolov@gmail.com #
#  https://t.me/ZbxNTg #
########################
# https://github.com/xxsokolov/Zabbix-Notification-Telegram
__author__ = "Sokolov Dmitry"
__maintainer__ = "Sokolov Dmitry"
__license__ = "MIT"
import telebot
from telebot import apihelper
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from zbxTelegram_files.classes.argparser import ArgParsing
import xmltodict
from zbxTelegram_config import *
import requests
from requests.adapters import HTTPAdapter
import urllib3
from urllib3.util.retry import Retry
import re
import sys
import os
import io
from PIL import Image, ImageDraw, ImageFont
import json
from errno import ENOENT
import logging
import html
import random
import string
import time
import tempfile

I18N = {
    "ru": {
        "t2i_fallback": "Ошибка при генерации изображения. Отправлено текстовое сообщение.",
        "t2i_no_pillow": "Библиотека Pillow не установлена. Отправлено текстовое сообщение.",
        "keys": {
            "Боғлама номи": "Группа",
            "Боғлама": "Группа",
            "ЭАТС": "Подгруппа",
            "Курилма номи": "Имя хоста",
            "Курилма тури": "Тип устройства",
            "Курилма урнатилган жой": "Расположение",
            "Курилма уланиши": "Uplink",
            "Курилма уланиши ( UPLINK )": "Uplink",
            "Курилма IP адреси": "IP адрес",
            "Курилма IР адреси": "IP адрес",
            "Курилма ИП адреси": "IP адрес",
            "Курилма ўтказувчанлик сиғими": "Пропускная способность",
            "Монтированная ёмкость": "Монтированная ёмкость",
            "Умумий абонентлар сони": "Всего абонентов",
            "Сана": "Дата",
            "Давомийлиги": "Продолжительность",
            "Статус": "Статус",
            "Курилма ўчиш вақти": "Время отключения",
            "Носозлик сабаби": "Причина неисправности",
            "Курилма ёнган вақти": "Время восстановления",
            "Диспетчер 1 статус": "Статус диспетчера 1",
            "Диспетчер 2 статус": "Статус диспетчера 2",
            "RCA причина": "RCA причина"
        }
    },
    "en": {
        "t2i_fallback": "Error during image generation. Text message sent instead.",
        "t2i_no_pillow": "Pillow library is not installed. Text message sent instead.",
        "keys": {
            "Боғлама номи": "Group",
            "Боғлама": "Group",
            "ЭАТС": "Subgroup",
            "Курилма номи": "Host Name",
            "Курилма тури": "Device Type",
            "Курилма урнатилган жой": "Location",
            "Курилма уланиши": "Uplink",
            "Курилма уланиши ( UPLINK )": "Uplink",
            "Курилма IP адреси": "IP Address",
            "Курилма IР адреси": "IP Address",
            "Курилма ўтказувчанлик сиғими": "Bandwidth",
            "Монтированная ёмкость": "Installed Capacity",
            "Умумий абонентлар сони": "Total Subscribers",
            "Сана": "Date",
            "Давомийлиги": "Duration",
            "Статус": "Status",
            "Курилма ўчиш вақти": "Downtime",
            "Носозлик сабаби": "Reason",
            "Курилма ёнган вақти": "Uptime",
            "Диспетчер 1 статус": "Dispatcher 1 status",
            "Диспетчер 2 статус": "Dispatcher 2 status",
            "RCA причина": "RCA reason"
        }
    },
    "uz": {
        "t2i_fallback": "Rasm yaratishda xatolik. Matn xabari yuborildi.",
        "t2i_no_pillow": "Pillow kutubxonasi o'rnatilmagan. Matn xabari yuborildi.",
        "keys": {
            "Боғлама номи": "Bog'lama",
            "Боғлама": "Bog'lama",
            "ЭАТС": "EATS",
            "Курилма номи": "Qurilma nomi",
            "Курилма тури": "Qurilma turi",
            "Курилма урнатилган жой": "Qurilma o'rnatilgan joy",
            "Курилма уланиши": "Qurilma ulanishi",
            "Курилма уланиши ( UPLINK )": "Qurilma ulanishi (uplink)",
            "Курилма IP адреси": "Qurilma IP manzili",
            "Курилма IР адреси": "Qurilma IP manzili",
            "Курилма ИП адреси": "Qurilma IP manzili",
            "Курилма ўтказувчанлик сиғими": "O'tkazuvchanlik sig'imi",
            "Сана": "Sana",
            "Давомийлиги": "Davomiyligi",
            "Статус": "Holat",
            "Курилма ўчиш вақти": "Qurilma o'chish vaqti",
            "Носозлик сабаби": "Nosozlik sababi",
            "Курилма ёнган вақти": "Qurilma tiklangan vaqti",
            "Диспетчер 1 статус": "Dispetcher 1 holati",
            "Диспетчер 2 статус": "Dispetcher 2 holati",
            "RCA причина": "RCA sababi"
        }
    }
}


class System:
    def __init__(self, debug=False):
        # configuring log
        if debug:
            self.log_level = logging.DEBUG
        else:
            self.log_level = logging.INFO

        log_format = logging.Formatter(
            '[%(asctime)s] - PID:%(process)s - %(funcName)s() - %(filename)s:%(lineno)d - %(levelname)s: %(message)s')
        self.log = logging.getLogger()
        self.log.setLevel(self.log_level)

        # Avoid duplicate handlers in long-running mode/import scenarios.
        if self.log.handlers:
            return

        # writing to stdout
        stdout_handler = logging.StreamHandler(sys.stdout)
        # stdout_handler = logging.StreamHandler(codecs.getwriter("utf-8")(sys.stdout.detach()))
        stdout_handler.setLevel(self.log_level)
        stdout_handler.setFormatter(log_format)
        # writing to file
        file_handler = logging.FileHandler(filename=config_log_file, mode='a')
        file_handler.setLevel(self.log_level)
        file_handler.setFormatter(log_format)

        self.log.addHandler(stdout_handler)
        self.log.addHandler(file_handler)


class FailSafeDict(dict):
    def __missing__(self, key):
        return '{{key not found: {}}}'.format(key)


args = ArgParsing().create_parser().parse_args(sys.argv[1:])
loggings = System(config_debug_mode if not args.debug else True).log
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
bot = telebot.TeleBot(args.token if args.token else tg_token)
if tg_proxy:
    apihelper.proxy = tg_proxy_server

HTTP_TIMEOUT = (3.05, 10)


def _build_http_session():
    session = requests.Session()
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        status=3,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET", "POST"])
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=20, pool_maxsize=50)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


HTTP = _build_http_session()


def parse_bool(value, default=False):
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    normalized = str(value).strip().lower()
    if normalized in ("1", "true", "yes", "on", "y"):
        return True
    if normalized in ("0", "false", "no", "off", "n"):
        return False
    return default


def zbx_api_call(payload, timeout=HTTP_TIMEOUT):
    url = zabbix_api_url.rstrip('/') + "/api_jsonrpc.php"
    headers = {'Content-Type': 'application/json-rpc'}
    response = HTTP.post(url, json=payload, headers=headers, verify=False, timeout=timeout)
    response.raise_for_status()
    data = response.json()
    if data.get("error"):
        raise RuntimeError("Zabbix API error: {}".format(data.get("error")))
    return data.get("result")


def ensure_parent_dir(path):
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def atomic_write_json(path, obj):
    ensure_parent_dir(path)
    fd, tmp_path = tempfile.mkstemp(prefix=".tmp_", suffix=".json", dir=os.path.dirname(path) or ".")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, sort_keys=True, ensure_ascii=False, indent=4)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def read_json_file(path, default=None):
    if default is None:
        default = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return default
            return json.loads(content)
    except FileNotFoundError:
        return default
    except Exception as err:
        loggings.warning("Cannot parse JSON file {}: {}".format(path, err))
        return default


def xml_parsing(data):
    try:
        raw_data = data
        if isinstance(data, str):
            data = data.strip()
        if not data:
            raise ValueError("Empty data")
        
        # Find the start of XML if it's prefixed with text (like Zabbix escalation notes)
        start_idx = -1
        if "<?xml" in data:
            start_idx = data.find("<?xml")
        elif "<root" in data:
            start_idx = data.find("<root")
            
        if start_idx != -1:
            data = data[start_idx:]
            
        data = dict(xmltodict.parse(data, process_namespaces=True)['root'])

        message = data['body']['messages']

        settings_graphs_bool = data.get('settings', {}).get('graphs', 'True')
        settings_graphlinks_bool = data.get('settings', {}).get('graphlinks', 'True')
        settings_triggerlinks_bool = data.get('settings', {}).get('triggerlinks', 'True')
        settings_hostlinks_bool = data.get('settings', {}).get('hostlinks', 'True')
        settings_acklinks_bool = data.get('settings', {}).get('acklinks', 'True')
        settings_eventlinks_bool = data.get('settings', {}).get('eventlinks', 'True')
        settings_eventtag_bool = data.get('settings', {}).get('eventtag', 'True')
        settings_eventidtag_bool = data.get('settings', {}).get('eventidtag', 'True')
        settings_itemidtag_bool = data.get('settings', {}).get('itemidtag', 'True')
        settings_triggeridtag_bool = data.get('settings', {}).get('triggeridtag', 'True')
        settings_actionidtag_bool = data.get('settings', {}).get('actionidtag', 'True')
        settings_hostidtag_bool = data.get('settings', {}).get('hostidtag', 'True')
        settings_zntsettingstag_bool = data.get('settings', {}).get('zntsettingstag', 'True')
        settings_mentions_bool = data.get('settings', {}).get('zntmentions', 'True')
        settings_keyboard = data.get('settings', {}).get('keyboard', 'True')
        settings_graphs_period = data.get('settings', {}).get('graphs_period', 'default')
        settings_host = data.get('settings', {}).get('host', '')
        settings_itemid = data.get('settings', {}).get('itemid', '')
        settings_triggerid = data.get('settings', {}).get('triggerid', '')
        settings_eventid = data.get('settings', {}).get('eventid', '')
        settings_actionid = data.get('settings', {}).get('actionid', '')
        settings_hostid = data.get('settings', {}).get('hostid', '')
        settings_title = data.get('settings', {}).get('title', 'Zabbix Alert')
        settings_trigger_url = data.get('settings', {}).get('triggerurl', '')
        settings_eventtags = data.get('settings', {}).get('eventtags', '')

        return dict(title=settings_title, message=message, eventtags=settings_eventtags,
                    settings_graphs_bool=parse_bool(settings_graphs_bool, True),
                    settings_graphlinks_bool=parse_bool(settings_graphlinks_bool, True),
                    settings_triggerlinks_bool=parse_bool(settings_triggerlinks_bool, True),
                    settings_hostlinks_bool=parse_bool(settings_hostlinks_bool, True),
                    settings_acklinks_bool=parse_bool(settings_acklinks_bool, True),
                    settings_eventlinks_bool=parse_bool(settings_eventlinks_bool, True),
                    settings_eventtag_bool=parse_bool(settings_eventtag_bool, True),
                    settings_eventidtag_bool=parse_bool(settings_eventidtag_bool, True),
                    settings_itemidtag_bool=parse_bool(settings_itemidtag_bool, True),
                    settings_triggeridtag_bool=parse_bool(settings_triggeridtag_bool, True),
                    settings_actionidtag_bool=parse_bool(settings_actionidtag_bool, True),
                    settings_hostidtag_bool=parse_bool(settings_hostidtag_bool, True),
                    settings_zntsettingstag_bool=parse_bool(settings_zntsettingstag_bool, True),
                    settings_zntmentions_bool=parse_bool(settings_mentions_bool, True),
                    settings_keyboard_bool=parse_bool(settings_keyboard, True),
                    graphs_period=settings_graphs_period, host=settings_host, itemid=settings_itemid,
                    triggerid=settings_triggerid, triggerurl=settings_trigger_url, eventid=settings_eventid,
                    actionid=settings_actionid, hostid=settings_hostid)

    except Exception as err:
        loggings.error("XML parsing error or missing tags: {}. Data start: {!r}. Using fallback (plain text mode).".format(err, raw_data[:100] if isinstance(raw_data, str) else "Non-string data"))
        # Fallback dictionary for plain text alerts
        return dict(title="Zabbix Alert", message=data, eventtags="",
                    settings_graphs_bool=False,
                    settings_graphlinks_bool=False,
                    settings_triggerlinks_bool=False,
                    settings_hostlinks_bool=False,
                    settings_acklinks_bool=False,
                    settings_eventlinks_bool=False,
                    settings_eventtag_bool=False,
                    settings_eventidtag_bool=False,
                    settings_itemidtag_bool=False,
                    settings_triggeridtag_bool=False,
                    settings_actionidtag_bool=False,
                    settings_hostidtag_bool=False,
                    settings_zntsettingstag_bool=True, # Enable ZNTSettings for tag parsing even in fallback
                    settings_zntmentions_bool=False,
                    settings_keyboard_bool=False,
                    graphs_period=None, host="", itemid="",
                    triggerid="", triggerurl="", eventid="",
                    actionid="", hostid="")


def watermark_text(img):
    img = io.BytesIO(img)
    img = Image.open(img)
    if img.height < watermark_minimal_height:
        loggings.info("Cannot set watermark text, img height {} (min. {})".format(img.height, watermark_minimal_height))
        return False
    font = ImageFont.truetype(watermark_font, 14)

    line_height = sum(font.getmetrics())

    try:
        left, top, right, bottom = font.getbbox(watermark_label)
        font_width = right - left
    except AttributeError:
        font_width = font.getsize(watermark_label)[0]

    fontimage = Image.new('L', (font_width, line_height))
    ImageDraw.Draw(fontimage).text((0, 0), watermark_label, fill=watermark_fill, font=font)
    fontimage = fontimage.rotate(watermark_rotate,  resample=Image.BICUBIC, expand=True)

    img_size = img.crop().size
    size = (img_size[0]-fontimage.size[0]-5, img_size[1]-fontimage.size[1]-10)

    img.paste(watermark_text_color, box=size, mask=fontimage)

    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format=img.format)
    img_byte_arr = img_byte_arr.getvalue()

    return img_byte_arr


def create_alert_image(data_dict, output_path, title_text=None, alert_type=None, lang="en"):
    # Define colors (Modern, vibrant palette)
    color_white = (255, 255, 255)
    color_black = (0, 0, 0)
    
    # Severity/Status colors
    # Problem (Red): #FF3B30
    # Resolved/OK (Green): #28CD41
    # Warning (Yellow): #FFCC00
    # Information (Blue): #007AFF
    # Disaster (Deep Red): #8B0000
    
    severity_colors = {
        "Problem": (255, 59, 48),    # Red
        "Resolved": (40, 205, 65),   # Green
        "OK": (40, 205, 65),         # Green
        "Information": (0, 122, 255),# Blue
        "Warning": (255, 204, 0),    # Yellow
        "Average": (255, 149, 0),    # Orange
        "High": (255, 59, 48),       # Red
        "Disaster": (139, 0, 0),     # Deep Red
    }
    
    header_color = severity_colors.get(alert_type, (142, 142, 147)) # Default gray
    
    # Row background colors (matching example screenshots)
    bg_red = (255, 0, 0)             # Red background for downtime row
    bg_yellow = (255, 255, 0)        # Yellow background for cause row
    bg_green = (146, 208, 80)        # Green background for recovery row
    color_gray = (180, 180, 180)     # Thin grid line color
    
    # Strong text colors for keywords
    strong_red = (255, 59, 48)
    strong_green = (40, 205, 65)
    
    # Font loading
    font = None
    font_bold = None
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf"
    ]
    font_bold_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
    ]
    
    for f in font_paths:
        try:
            font = ImageFont.truetype(f, 20)
            break
        except IOError:
            continue
    for f in font_bold_paths:
        try:
            font_bold = ImageFont.truetype(f, 21)
            break
        except IOError:
            continue
            
    if not font:
        font = ImageFont.load_default()
    if not font_bold:
        font_bold = font

    def measure_text_width(text, use_font):
        if hasattr(use_font, "getbbox"):
            left, top, right, bottom = use_font.getbbox(str(text))
            return right - left
        if hasattr(use_font, "getsize"):
            return use_font.getsize(str(text))[0]
        return len(str(text)) * 8

    def wrap_text(text, use_font, max_width):
        text = str(text) if text is not None else ""
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        def split_long_token(token):
            # Split long chunks without spaces (hostnames/IDs) to avoid clipping.
            if measure_text_width(token, use_font) <= max_width:
                return [token]
            chunks = []
            chunk = ""
            for ch in token:
                candidate = chunk + ch
                if chunk and measure_text_width(candidate, use_font) > max_width:
                    chunks.append(chunk)
                    chunk = ch
                else:
                    chunk = candidate
            if chunk:
                chunks.append(chunk)
            return chunks

        parts = []
        for paragraph in text.split("\n"):
            words = paragraph.split()
            if not words:
                parts.append("")
                continue
            expanded = []
            for w in words:
                expanded.extend(split_long_token(w))
            line = expanded[0]
            for w in expanded[1:]:
                candidate = line + " " + w
                if measure_text_width(candidate, use_font) <= max_width:
                    line = candidate
                else:
                    parts.append(line)
                    line = w
            parts.append(line)
        return parts if parts else [""]

    def normalize_value_for_lang(v, current_lang):
        s = str(v).strip()
        if current_lang != "uz":
            return s

        replacements = [
            ("Не подтвержден", "Tasdiqlanmagan"),
            ("Подтвержден", "Tasdiqlangan"),
            ("Not confirmed", "Tasdiqlanmagan"),
            ("Confirmed", "Tasdiqlangan"),
            ("current:", "joriy:"),
            ("Current:", "Joriy:"),
            ("Unavailable by ICMP ping", "ICMP ping orqali javob yo'q"),
            ("ICMP Ping:", "ICMP ping:"),
            ("Up (", "Ishlamoqda ("),
            ("Resolved", "Tiklangan"),
            ("Problem", "Muammo"),
            ("Warning", "Ogohlantirish"),
            ("High", "Yuqori"),
            ("Average", "O'rtacha"),
            ("Disaster", "Favqulodda")
        ]
        for src, dst in replacements:
            s = s.replace(src, dst)
        return s

    # Translate keys first
    translated_data = []
    for key, value in data_dict.items():
        # Normalize key by stripping and replacing Uzbek variants to simplify dictionary
        k = str(key).strip().replace('Қ', 'К').replace('қ', 'к').replace('ў', 'ў')
        v = str(value).strip()
        if lang in I18N and k in I18N[lang].get("keys", {}):
            translated_data.append((I18N[lang]["keys"][k], normalize_value_for_lang(v, lang)))
        else:
            translated_data.append((k, normalize_value_for_lang(v, lang)))

    # Table settings
    row_height = 40
    line_height = sum(font.getmetrics()) + 4 if hasattr(font, "getmetrics") else 24
    col1_width = 300
    col2_width = 600
    
    # Extract Date/Сана/Дата to use as title if not provided
    extracted_date = None
    new_translated_data = []
    for k, v in translated_data:
        if any(d in str(k).strip() for d in ["Дата", "Сана", "Date"]):
            extracted_date = v
        else:
            new_translated_data.append((k, v))
            
    translated_data = new_translated_data
    if not title_text and extracted_date:
        title_text = extracted_date

    wrapped_rows = []
    key_text_width = col1_width - 20
    value_text_width = col2_width - 20
    for key, value in translated_data:
        k_lines = wrap_text(key, font, key_text_width)
        v_lines = wrap_text(value, font, value_text_width)
        lines_count = max(len(k_lines), len(v_lines), 1)
        row_h = max(row_height, lines_count * line_height + 10)
        wrapped_rows.append((key, value, k_lines, v_lines, row_h))

    total_width = col1_width + col2_width
    total_height = sum(r[4] for r in wrapped_rows) + (row_height if title_text else 0)

    img = Image.new('RGB', (total_width, total_height), color=color_white)
    draw = ImageDraw.Draw(img)
    
    y = 0
    
    # Draw title
    if title_text:
        draw.rectangle([(0, y), (col1_width, y + row_height)], fill=color_white, outline=color_gray, width=1)
        draw.rectangle([(col1_width, y), (total_width, y + row_height)], fill=color_white, outline=color_gray, width=1)
        # Center title text in the second column
        if hasattr(draw, 'textlength'):
            tw = draw.textlength(str(title_text), font=font_bold)
        elif hasattr(font_bold, 'getsize'):
            tw = font_bold.getsize(str(title_text))[0]
        else:
            left, top, right, bottom = font_bold.getbbox(str(title_text))
            tw = right - left
        
        draw.text((col1_width + (col2_width - tw) / 2, y + 5), str(title_text), font=font_bold, fill=color_black)
        y += row_height

    # Draw rows
    for key, value, key_lines, value_lines, row_h in wrapped_rows:
        bg_color = color_white
        text_color = color_black
        value_text_color = color_black
        key_lower = str(key).lower()
        display_key = str(key)
        
        # Determine label, background, and text color based on key content
        is_downtime_row = any(word in key_lower for word in ["ўчиш", "отключени", "downtime", "время отключения"])
        is_uptime_row = any(word in key_lower for word in ["ёнган", "восстановлени", "uptime", "время восстановления"])
        is_cause_row = any(word in key_lower for word in ["носозлик", "сабаби", "причина", "reason", "неисправность"])
        
        if is_downtime_row:
            if alert_type == "Resolved":
                bg_color = bg_green
                # display_key = "Время восстановления" if lang == "ru" else "Қурилма ёнган вақти"
            else:
                bg_color = bg_red
            text_color = color_black
            value_text_color = color_black
        elif is_uptime_row:
            bg_color = bg_green
            text_color = color_black
            value_text_color = color_black
        elif is_cause_row:
            bg_color = bg_yellow
            text_color = color_black
            value_text_color = color_black
            
        draw.rectangle([(0, y), (col1_width, y + row_h)], fill=bg_color, outline=color_gray, width=1)
        for i, line in enumerate(key_lines):
            draw.text((10, y + 5 + i * line_height), line, font=font, fill=text_color)
        
        draw.rectangle([(col1_width, y), (total_width, y + row_h)], fill=bg_color, outline=color_gray, width=1)
        
        for i, line in enumerate(value_lines):
            draw.text((col1_width + 10, y + 5 + i * line_height), line, font=font, fill=value_text_color)
        
        y += row_h

    img.save(output_path)
    return True


def get_cookie():
    try:
        data_api = {"name": zabbix_api_login, "password": zabbix_api_pass, "enter": "Sign in"}
        req_cookie = HTTP.post(zabbix_api_url, data=data_api, verify=False, timeout=HTTP_TIMEOUT)
        req_cookie.raise_for_status()
        cookie = req_cookie.cookies
        req_cookie.close()
        if not any(_ in cookie for _ in ['zbx_session', 'zbx_sessionid']):
            loggings.error(
                'User authorization failed: {} ({})'.format('Login name or password is incorrect.', zabbix_api_url))
            return False
        return cookie
    except Exception as err:
        loggings.error("Cannot get cookie from {}: {}".format(zabbix_api_url, err))
        return False


def get_host_macros(hostid):
    """Fetch user macros for a specific host from Zabbix API"""
    try:
        auth_payload = {
            "jsonrpc": "2.0",
            "method": "user.login",
            "params": {"username": zabbix_api_login, "password": zabbix_api_pass},
            "id": 1
        }
        auth_token = zbx_api_call(auth_payload)
        
        if not auth_token:
            return {}
            
        # Get macros
        macro_payload = {
            "jsonrpc": "2.0",
            "method": "host.get",
            "params": {
                "output": ["hostid"],
                "selectMacros": "extend",
                "hostids": hostid
            },
            "auth": auth_token,
            "id": 2
        }
        result = zbx_api_call(macro_payload) or []
        
        macros_dict = {}
        if result and len(result) > 0:
            for m in result[0].get('macros', []):
                macros_dict[m['macro']] = m['value']
                
        return macros_dict
    except Exception as e:
        loggings.error("Error fetching host macros: {}".format(e))
        return {}


def get_event_dispatch_info(eventid):
    """Fetch dispatcher confirmations and latest RCA/problem reason from acknowledgements."""
    try:
        if not eventid:
            return {
                "dispatcher1_confirmed": False,
                "dispatcher2_confirmed": False,
                "reason_comment": ""
            }

        auth_payload = {
            "jsonrpc": "2.0",
            "method": "user.login",
            "params": {"username": zabbix_api_login, "password": zabbix_api_pass},
            "id": 1
        }
        auth_token = zbx_api_call(auth_payload)
        if not auth_token:
            return {
                "dispatcher1_confirmed": False,
                "dispatcher2_confirmed": False,
                "reason_comment": ""
            }

        ack_payload = {
            "jsonrpc": "2.0",
            "method": "event.get",
            "params": {
                "output": ["eventid"],
                "eventids": [str(eventid)],
                "selectAcknowledges": ["message", "clock"],
                "source": 0,
                "object": 0
            },
            "auth": auth_token,
            "id": 2
        }
        result = zbx_api_call(ack_payload) or []
        if not result:
            return {
                "dispatcher1_confirmed": False,
                "dispatcher2_confirmed": False,
                "reason_comment": ""
            }

        acks = result[0].get("acknowledges", []) or []
        if not acks:
            return {
                "dispatcher1_confirmed": False,
                "dispatcher2_confirmed": False,
                "reason_comment": ""
            }

        # newest first
        acks = sorted(acks, key=lambda a: int(a.get("clock", 0)), reverse=True)
        d1 = False
        d2 = False
        rca_reason = ""
        fallback_comment = ""

        for ack in acks:
            msg = (ack.get("message") or "").strip()
            if not msg:
                continue

            if msg.startswith("[DISP1_ACK]"):
                d1 = True
                continue
            if msg.startswith("[DISP2_ACK]"):
                d2 = True
                continue

            is_rca = msg.startswith("[RCA]")
            if is_rca:
                msg = msg.replace("[RCA]", "", 1).strip()
            # remove trailing service part "(by ... at ...)" for cleaner card line
            msg = re.sub(r"\s*\(by .+ at .+\)\s*$", "", msg, flags=re.IGNORECASE)
            if not msg:
                continue
            if is_rca:
                rca_reason = msg
                break
            if not fallback_comment:
                fallback_comment = msg

        return {
            "dispatcher1_confirmed": d1,
            "dispatcher2_confirmed": d2,
            "reason_comment": rca_reason or fallback_comment
        }
    except Exception as e:
        loggings.warning("Cannot fetch dispatch comments for event {}: {}".format(eventid, e))
        return {
            "dispatcher1_confirmed": False,
            "dispatcher2_confirmed": False,
            "reason_comment": ""
        }


def get_chart_png(itemid, graff_name, period=None):
    try:
        cookies = get_cookie()
        if cookies:
            response = HTTP.get(zabbix_graph_chart.format(
                name=graff_name,
                itemid=itemid,
                zabbix_server=zabbix_api_url,
                range_time=period),
                cookies=cookies,
                verify=False,
                timeout=HTTP_TIMEOUT)
            response.raise_for_status()

            if watermark:
                wmt = watermark_text(response.content)
                if wmt:
                    return dict(img=wmt, url=response.url)
                else:
                    return dict(img=response.content, url=response.url)
            else:
                return dict(img=response.content, url=response.url)
        else:
            return dict(img=None, url=None)
    except Exception as err:
        loggings.error("Cannot build chart PNG for item {}: {}".format(itemid, err), exc_info=config_exc_info)
        return dict(img=None, url=None)


def create_tags_list(_bool=False, tag=None, _type=None, zntsettingstag=False):
    tags_list = []
    settings_list = []
    try:
        if _bool:
            if tag and (re.search(r'\w', tag)):
                for tags in tag.split(', '):
                    if tags:
                        if not zntsettingstag:
                            if tags.find(':') != -1:
                                tag, value = re.split(r':+',tags, maxsplit=1)
                                if tag != trigger_settings_tag and tag != trigger_info_mentions_tag:
                                    tags_list.append('#{tag}_{value}'.format(
                                        tag=_type + re.sub(r"\W+", "_", tag) if _type else re.sub(r"\W+", "_", tag),
                                        value=re.sub(r"\W+", "_", value)))
                                else:
                                    continue
                            else:
                                if len(tags.split()) > 0:
                                    for tg_s in tags.split():
                                        tags_list.append('#{tag}'.format(
                                            tag=_type + re.sub(r"\W+", "_", tg_s) if _type else re.sub(r"\W+", "_", tg_s)))
                                else:
                                    tags_list.append('#{tag}'.format(
                                        tag=_type + re.sub(r"\W+", "_", tags) if _type else re.sub(r"\W+", "_", tags)))
                        else:
                            if tags.find(':') != -1:
                                tag, value = re.split(r':+',tags, maxsplit=1)
                                if tag == trigger_settings_tag:
                                    tags_list.append('#{tag}_{value}'.format(
                                        tag=_type + re.sub(r"\W+", "_", tag) if _type else re.sub(r"\W+", "_", tag),
                                        value=re.sub(r"\W+", "_", value)))
                                    settings_list.append(value)
                                else:
                                    continue
                            else:
                                continue
                    else:
                        tags_list.append(body_messages_tags_no)
            else:
                tags_list.append(body_messages_tags_no)
        else:
            return False

    except ValueError:
        tags_list.append(body_messages_tags_no)
    else:
        return body_messages_tags_delimiter.join(tags_list) if not zntsettingstag else {
            'tags': body_messages_tags_delimiter.join(tags_list),
            trigger_settings_tag: settings_list}


def create_mentions_list(_bool=False, mentions=None):
    mentions_list = []
    try:
        if _bool and mentions:
            for tags in mentions.split(', '):
                if tags.find(':') != -1:
                    tag, value = re.split(r':+',tags, maxsplit=1)
                    if tag == trigger_info_mentions_tag:
                        for username in value.split():
                            mentions_list.append(username)
            return mentions_list
        else:
            return False
    except Exception as err:
        loggings.error("Cannot parse mentions: {}".format(err), exc_info=config_exc_info)
        return []


def create_links_list(_bool=None, url=None, _type=None, url_list=None):
    try:
        if _bool:
            if url and (re.search(r'\w', url)):
                return body_messages_url_template.format(url=url, icon=_type)
            else:
                return body_messages_url_emoji_no_url
        elif url_list:
            return url_list
        else:
            return False
    except ValueError:
        return body_messages_url_emoji_no_url


def get_cache(title):
    cache = read_json_file(config_cache_file, default={})
    if not cache:
        return False
    for name, value in cache.items():
        if title == name and isinstance(value, dict):
            return value.get('id')
    return False


def set_cache(title, send_id, sent_type, cache=None, update=None):
    cache = read_json_file(config_cache_file, default={})
    if not isinstance(cache, dict):
        cache = {}
    if not update:
        cache[title] = dict(type=str(sent_type), id=str(send_id))
    else:
        cache[title] = dict(type=str(sent_type), id=str(send_id), old=str(update))
    atomic_write_json(config_cache_file, cache)
    if update:
        loggings.info("Updated id for {} ({}): old '{}' -> new '{}' in cache file".format(
            title, sent_type, update, send_id))
    else:
        loggings.info("Add new id {} for {} ({}) in cache file".format(send_id, title, sent_type))
    return True


def get_event_cache(chat_id, eventid):
    try:
        cache = read_json_file(config_event_cache_file, default={})
        key = "{}:{}".format(chat_id, eventid)
        return cache.get(key)
    except Exception as err:
        loggings.error("Error reading event cache: {}".format(err))
        return False


def set_event_cache(chat_id, eventid, message_id):
    cache = {}
    try:
        cache = read_json_file(config_event_cache_file, default={})
        if not isinstance(cache, dict):
            cache = {}
        
        key = "{}:{}".format(chat_id, eventid)
        cache[key] = message_id
        
        # Limit cache size to 1000 entries to prevent file bloat
        if len(cache) > 1000:
            # Remove oldest entries (keys are not necessarily ordered, but this is a simple heuristic)
            keys = list(cache.keys())
            for k in keys[:100]:
                del cache[k]

        atomic_write_json(config_event_cache_file, cache)
        return True
    except Exception as err:
        loggings.error("Error writing event cache: {}".format(err))
        return False


def migrate_group_id(sent_to, sent_id, err):
    for key, value in json.loads(err.result.text).items():
        if key == 'parameters' and value['migrate_to_chat_id']:
            loggings.warning("Group chat was upgraded to a supergroup chat ({})".format(value['migrate_to_chat_id']),
                             exc_info=config_exc_info)
            set_cache(sent_to, value['migrate_to_chat_id'], 'supergroup', update=sent_id)


def get_send_id(send_to):
    try:
        chat = None
        if re.search('^-?[0-9]+$', str(send_to)):
            return str(send_to)
        elif str(send_to).startswith('@'):
            send_to = send_to.replace("@", "")
        elif not send_to:
            raise ValueError('Username or groupname is not specified. You can use for username '
                             '@[a-z,A-Z,0-9 and underscores] and for groupname any characters. ')

        send_id = get_cache(send_to)

        if send_id:
            return send_id

        loggings.info("Telegram API: method getUpdate: started")
        get_updates_list = bot.get_updates(timeout=10)
        sum_del_update_id = 0
        while len([value.update_id for value in get_updates_list]) >= 100:
            sum_del_update_id += len([value.update_id for value in get_updates_list])
            get_updates_list = bot.get_updates(timeout=10, offset=max([value.update_id for value in get_updates_list]))

        if sum_del_update_id > 0:
            loggings.info("In getUpdate list was cleared {} messages. Submitted for processing {}.".format(
                sum_del_update_id, len([value.update_id for value in get_updates_list])))

        for line in get_updates_list:
            if line.message:
                chat = line.message.chat
            elif line.edited_message:
                chat = line.edited_message.chat
            elif line.channel_post:
                chat = line.channel_post.chat

            if chat.type in ["group", "supergroup"] and chat.title and chat.title == send_to:
                if not send_id:
                    set_cache(send_to, chat.id, chat.type)
                bot.get_updates(timeout=10, offset=-1)
                return chat.id

            if chat.type in ["channel"] and chat.title and chat.title == send_to:
                if not send_id:
                    set_cache(send_to, chat.id, chat.type)
                bot.get_updates(timeout=10, offset=-1)
                return chat.id

            if chat.type in ["private"] and chat.username == send_to.replace("@", ""):
                if not send_id:
                    set_cache(send_to, chat.id, chat.type)
                bot.get_updates(timeout=10, offset=-1)
                return chat.id

        raise ValueError('Username or groupname not found in the cache file. No access occurred or bot is not added to '
                         'group "{sendto}" (Add bot group and/or send message to {bot})'.format(
            bot=bot.get_me().username,
            sendto=send_to))
    except Exception as err:
        loggings.error("Cannot resolve Telegram recipient '{}': {}".format(send_to, err), exc_info=config_exc_info)
        return False


def gen_markup(eventid):
    send_message_button = globals().get('zabbix_keyboard_button_sendmessage', '✍ Изоҳ')
    markup = InlineKeyboardMarkup()
    markup.row_width = zabbix_keyboard_row_width
    markup.add(
        InlineKeyboardButton(zabbix_keyboard_button_message,
                             callback_data='{}'.format(json.dumps(dict(action="messages", eventid=eventid)))),
        InlineKeyboardButton(send_message_button,
                             callback_data='{}'.format(json.dumps(dict(action="add_message", eventid=eventid)))),
        InlineKeyboardButton(zabbix_keyboard_button_acknowledge,
                             callback_data='{}'.format(json.dumps(dict(action="acknowledge", eventid=eventid)))),
        InlineKeyboardButton(zabbix_keyboard_button_history,
                             callback_data='{}'.format(json.dumps(dict(action="history", eventid=eventid)))))
    return markup


def send_messages(sent_to, message, graphs_png, eventid=None, settings_keyboard=None, disable_notification=False, reply_to_message_id=None):
    try:
        sent_id = get_send_id(sent_to)
        if not sent_id:
            loggings.error("Skip send: cannot resolve destination '{}'".format(sent_to))
            return False
        if message and sent_to:
            if graphs_png and isinstance(graphs_png, list):
                try:
                    graphs_png[0].caption = message
                    graphs_png[0].parse_mode = "HTML"
                    sent_msg = bot.send_media_group(chat_id=sent_id, media=graphs_png, disable_notification=disable_notification, reply_to_message_id=reply_to_message_id)
                except apihelper.ApiException as err:
                    if 'migrate_to_chat_id' in err.result.text:
                        migrate_group_id(sent_to, sent_id, err)
                        return send_messages(sent_to, message, graphs_png, eventid=eventid, settings_keyboard=settings_keyboard, disable_notification=disable_notification, reply_to_message_id=reply_to_message_id)
                    else:
                        loggings.error("Telegram API error (media_group): {}".format(err), exc_info=config_exc_info)
                        return False
                except Exception as err:
                    loggings.error("Unexpected send_media_group error: {}".format(err), exc_info=config_exc_info)
                    return False
                else:
                    loggings.info('Bot @{busername}({bid}) send media group to "{sent_to}" ({sent_id}).'.format(
                        sent_to=sent_to, sent_id=sent_id, busername=bot.get_me().username, bid=bot.get_me().id))
                    return sent_msg[0].message_id if sent_msg else True
            elif graphs_png and graphs_png.get('img'):
                try:
                    sent_msg = bot.send_photo(chat_id=sent_id, photo=graphs_png.get('img'), caption=message, parse_mode="HTML",
                                   reply_markup=gen_markup(eventid) if zabbix_keyboard and settings_keyboard else None,
                                   disable_notification=disable_notification, reply_to_message_id=reply_to_message_id)
                except apihelper.ApiException as err:
                    if 'migrate_to_chat_id' in err.result.text:
                        migrate_group_id(sent_to, sent_id, err)
                        return send_messages(sent_to, message, graphs_png, eventid=eventid, settings_keyboard=settings_keyboard, disable_notification=disable_notification, reply_to_message_id=reply_to_message_id)
                    elif 'IMAGE_PROCESS_FAILED' in err.result.text:
                        bot.send_photo(chat_id=sent_id, photo=open(
                              file='{0}/zbxTelegram_files/error_send_photo.png'.format(
                                  os.path.dirname(os.path.realpath(__file__))),
                              mode='rb').read(), caption=message, parse_mode="HTML",
                                       reply_markup=gen_markup(
                                           eventid) if zabbix_keyboard and settings_keyboard else None,
                                       disable_notification=disable_notification, reply_to_message_id=reply_to_message_id)
                    else:
                        loggings.error("Telegram API error (photo): {}".format(err), exc_info=config_exc_info)
                        return False
                except Exception as err:
                    loggings.error("Unexpected send_photo error: {}".format(err), exc_info=config_exc_info)
                    return False
                else:
                    loggings.info('Bot @{busername}({bid}) send photo to "{sent_to}" ({sent_id}).'.format(
                        sent_to=sent_to, sent_id=sent_id, busername=bot.get_me().username, bid=bot.get_me().id))
                    return sent_msg.message_id if sent_msg else True
            else:
                try:
                    sent_msg = bot.send_message(chat_id=sent_id, text=message, parse_mode="HTML", disable_web_page_preview=True,
                                     reply_markup=gen_markup(eventid) if zabbix_keyboard and settings_keyboard
                                     else None,
                                     disable_notification=disable_notification, reply_to_message_id=reply_to_message_id)
                except apihelper.ApiException as err:
                    if 'migrate_to_chat_id' in json.loads(err.result.text).get('parameters'):
                        migrate_group_id(sent_to, sent_id, err)
                        return send_messages(sent_to, message, graphs_png, eventid=eventid, settings_keyboard=settings_keyboard, disable_notification=disable_notification, reply_to_message_id=reply_to_message_id)
                    else:
                        loggings.error("Exception occurred in Api Telegram: {}".format(err), exc_info=config_exc_info)
                        return False
                except Exception as err:
                    loggings.error("Unexpected send_message error: {}".format(err), exc_info=config_exc_info)
                    return False
                else:
                    loggings.info('Bot @{busername}({bid}) send message to "{sent_to}" ({sent_id}).'.format(
                        sent_to=sent_to, sent_id=sent_id, busername=bot.get_me().username, bid=bot.get_me().id))
                    return sent_msg.message_id if sent_msg else True
    except Exception as err:
        loggings.error("Unexpected send_messages wrapper error: {}".format(err), exc_info=config_exc_info)
        return False


def set_period_day_hour(seconds):
    seconds = int(seconds)
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    if days > 0:
        return '{}d {}h'.format(days, hours) if hours > 0 else '{}d'.format(days)
    elif hours > 0:
        return '{}h {}m'.format(hours, minutes) if minutes > 0 else '{}h'.format(hours)
    elif minutes > 0:
        return '{}m'.format(minutes)


def main():
    graph_period = None
    graph_period_raw = None
    loggings.info("Send to {} action: {}".format(args.username, args.subject))
    loggings.debug("sys.argv: {}".format(sys.argv[1:]))
    loggings.debug("Send to {}\naction: {}\nxml: {}".format(args.username, args.subject, args.messages))

    is_test = False
    if (args.subject and args.subject.lower() in ['test subject', 'test', 'тестовая тема']) or \
            (args.messages and args.messages.lower() in ['this is the test message from zabbix', 'test', 'это тестовое сообщение от zabbix']):
        is_test = True

    if is_test:
        if get_cookie():
            loggings.info('Connection check passed ({})'.format(zabbix_api_url))
            test_graph_file = '{0}/zbxTelegram_files/test.png'
            error_code = 0
        else:
            test_graph_file = '{0}/zbxTelegram_files/error_send_photo.png'
            error_code = 1

        if "text2image" not in str(args.subject).lower() and "text2image" not in str(args.messages).lower():
            send_messages(sent_to=args.username, message='🚨 Test 🚽💩: Test message\n'
                                                         'Host: testhost [192.168.0.0]\n'
                                                         'Last value: test (10:00:00)\n'
                                                         'Duration: 1m\n'
                                                         'Description: This message is generated with test data. '
                                                         'specify as the topic and / or zabbix\n\n'
                                                         '#Test, #eid_130144443, #iid_60605, #tid_39303, #aid_22',
                          graphs_png=dict(
                              img=open(
                                  file=test_graph_file.format(os.path.dirname(os.path.realpath(__file__))),
                                  mode='rb').read()))
            exit(error_code)
        else:
            loggings.info("Test mode with text2image enabled")
            args.messages = '<?xml version="1.0" encoding="UTF-8" ?><root><body><messages><![CDATA[Host: testhost [192.168.1.1]\nLast value: 99% (10:00:00)\nDuration: 1m]]></messages></body><settings><graphs>False</graphs><title>Test Alert</title><eventtags>ZNTSettings:text2image, ZNTSettings:text2image_title=Test Alert</eventtags><host>testhost</host><itemid>12345</itemid><triggerid>67890</triggerid><eventid>11111</eventid><actionid>22222</actionid><hostid>33333</hostid><graphs_period>default</graphs_period><hostlinks>True</hostlinks><graphlinks>True</graphlinks><acklinks>True</acklinks><eventlinks>True</eventlinks><triggerlinks>True</triggerlinks><eventtag>True</eventtag><eventidtag>True</eventidtag><itemidtag>True</itemidtag><triggeridtag>True</triggeridtag><actionidtag>True</actionidtag><hostidtag>True</hostidtag><zntsettingstag>True</zntsettingstag><zntmentions>True</zntmentions><keyboard>True</keyboard><triggerurl>http://notes.com</triggerurl></settings></root>'

    data_zabbix = xml_parsing(args.messages)

    # Parse message body into a dictionary for image generation
    data_dict = {}
    if isinstance(data_zabbix['message'], str):
        for line in data_zabbix['message'].split('\n'):
            if ':' in line:
                k_orig, v_orig = line.split(':', 1)
                data_dict[k_orig.strip()] = v_orig.strip()

    # Fetch and inject host macros if hostid is available
    if data_zabbix.get('hostid'):
        macros = get_host_macros(data_zabbix['hostid'])
        if macros:
            # Map Zabbix macros to human-readable keys
            macro_mapping = {
                '{$HOST.DEVICE}': 'Курилма тури',
                '{$HOST.LOCATION}': 'Курилма урнатилган жой',
                '{$HOST.UPLINK}': 'Курилма уланиши ( UPLINK )'
            }
            for m_key, friendly_key in macro_mapping.items():
                if m_key in macros and friendly_key not in data_dict:
                    data_dict[friendly_key] = macros[m_key]

    # Add dispatcher confirmations + SSOT reason from DB acknowledgements/comments.
    if data_zabbix.get('eventid'):
        dispatch_info = get_event_dispatch_info(data_zabbix['eventid'])
        current_lang = str(tg_lang).lower() if 'tg_lang' in globals() else "en"
        if current_lang == "uz":
            d_ok, d_no = "Тасдиқланган", "Тасдиқланмаган"
        elif current_lang == "ru":
            d_ok, d_no = "Подтвержден", "Не подтвержден"
        else:
            d_ok, d_no = "Confirmed", "Not confirmed"

        data_dict['Диспетчер 1 статус'] = d_ok if dispatch_info.get('dispatcher1_confirmed') else d_no
        data_dict['Диспетчер 2 статус'] = d_ok if dispatch_info.get('dispatcher2_confirmed') else d_no

        reason_comment = str(dispatch_info.get('reason_comment', '') or '').strip()
        # Put SSOT reason into the existing "Носозлик сабаби" row, without a separate RCA row.
        if reason_comment:
            data_dict['Носозлик сабаби'] = reason_comment
        elif 'Носозлик сабаби' not in data_dict:
            data_dict['Носозлик сабаби'] = '-'
        data_dict.pop('RCA причина', None)

    event_tags = create_tags_list(
        _bool=True if data_zabbix.get('settings_eventtag_bool') and body_messages_tags_event else False,
        tag=data_zabbix['eventtags'], _type=None)
    eventid_tags = create_tags_list(
        _bool=True if data_zabbix.get('settings_eventidtag_bool') and body_messages_tags_eventid else False,
        tag=data_zabbix['eventid'], _type=body_messages_tags_prefix_eventid)
    itemid_tags = create_tags_list(
        _bool=True if data_zabbix.get('settings_itemidtag_bool') and body_messages_tags_itemid else False,
        tag=' '.join([item_id for item_id in data_zabbix['itemid'].split() if re.findall(r"\d+", item_id)]),
        _type=body_messages_tags_prefix_itemid)
    triggerid_tags = create_tags_list(
        _bool=True if data_zabbix.get('settings_triggeridtag_bool') and body_messages_tags_triggerid else False,
        tag=data_zabbix['triggerid'], _type=body_messages_tags_prefix_triggerid)
    actionid_tags = create_tags_list(
        _bool=True if data_zabbix.get('settings_actionidtag_bool') and body_messages_tags_actionid else False,
        tag=data_zabbix['actionid'], _type=body_messages_tags_prefix_actionid)
    hostid_tags = create_tags_list(
        _bool=True if data_zabbix.get('settings_hostidtag_bool') and body_messages_tags_hostid else False,
        tag=data_zabbix['hostid'], _type=body_messages_tags_prefix_hostid)
    zntsettings_tags = create_tags_list(
        _bool=True if data_zabbix.get('settings_zntsettingstag_bool') and body_messages_tags_trigger_settings
        else False,
        tag=data_zabbix['eventtags'], _type=None, zntsettingstag=True)

    mentions = create_mentions_list(
        _bool=True if data_zabbix.get('settings_zntmentions_bool') and body_messages_mentions_settings else False,
        mentions=data_zabbix['eventtags'])

    tags_list = []
    if isinstance(zntsettings_tags, dict) and len(zntsettings_tags[trigger_settings_tag]) > 0:
        loggings.info("Found settings tag: {}: {}".format(trigger_settings_tag,
                                                          ', '.join(zntsettings_tags[trigger_settings_tag])))
        tags_list.append(zntsettings_tags['tags']) if zntsettings_tags['tags'] else None
        if trigger_settings_tag_no_alert in zntsettings_tags[trigger_settings_tag]:
            loggings.info("Message sending canceled: {}:{}".format(trigger_settings_tag, trigger_settings_tag_no_alert))
            return 0

    tags_list.append(event_tags) if event_tags else None
    tags_list.append(eventid_tags) if eventid_tags else None
    tags_list.append(itemid_tags) if itemid_tags else None
    tags_list.append(triggerid_tags) if triggerid_tags else None
    tags_list.append(actionid_tags) if actionid_tags else None
    tags_list.append(hostid_tags) if hostid_tags else None


    trigger_url = create_links_list(
        _bool=True if data_zabbix.get('settings_triggerlinks_bool') and body_messages_url_notes else False,
        url=data_zabbix.get('triggerurl'),
        _type=body_messages_url_emoji_notes)

    host_url = create_links_list(
        _bool=True if data_zabbix.get('settings_hostlinks_bool') and body_messages_url_host else False,
        url=zabbix_host_link.format(zabbix_server=zabbix_api_url, host=data_zabbix.get('host')),
        _type=body_messages_url_emoji_host)

    ack_url = create_links_list(
        _bool=True if data_zabbix.get('settings_acklinks_bool') and body_messages_url_ack else False,
        url=zabbix_ack_link.format(zabbix_server=zabbix_api_url, eventid=data_zabbix.get('eventid')),
        _type=body_messages_url_emoji_ack)

    event_url = create_links_list(
        _bool=True if data_zabbix.get('settings_eventlinks_bool') and body_messages_url_event else False,
        url=zabbix_event_link.format(zabbix_server=zabbix_api_url, eventid=data_zabbix.get('eventid'),
                                     triggerid=data_zabbix.get('triggerid')), _type=body_messages_url_emoji_event)

    if isinstance(zntsettings_tags, dict) and trigger_settings_tag in zntsettings_tags:
        # Find period= setting if it exists
        period_setting = next((s for s in zntsettings_tags[trigger_settings_tag] if s.startswith(trigger_settings_tag_graph_period)), None)
        if period_setting:
            try:
                graph_period = int(period_setting.split('=')[1])
            except Exception as err:
                loggings.error("Exception occurred parsing graph period: {}, {}".format(period_setting, err))
                graph_period = zabbix_graph_period_default
        elif data_zabbix['graphs_period'] and data_zabbix['graphs_period'] != 'default':
            graph_period = data_zabbix['graphs_period']
        else:
            graph_period = zabbix_graph_period_default
    else:
        graph_period = zabbix_graph_period_default
        
    # Additional settings from tags
    text2image = False
    text2image_title = ""
    alert_type = ""
    try:
        lang = tg_lang
    except:
        lang = "en"

    if isinstance(zntsettings_tags, dict):
        for s in zntsettings_tags[trigger_settings_tag]:
            if s == "text2image":
                text2image = True
            elif s.startswith("text2image_title="):
                text2image_title = s.split("=", 1)[1]
            elif s.startswith("alert_type="):
                alert_type = s.split("=", 1)[1]
    
    url_list = []
    url_list.append(trigger_url) if trigger_url else None
    for item_id in list(set([x for x in data_zabbix.get('itemid').split()])):
        if re.findall(r"\d+", item_id):
            items_link = create_links_list(
                _bool=True if data_zabbix.get('settings_graphlinks_bool') and body_messages_url_graphs else False,
                url=zabbix_graph_link.format(zabbix_server=zabbix_api_url, itemid=item_id,
                                             range_time=data_zabbix['graphs_period']),
                _type=body_messages_url_emoji_graphs
                                           )
            url_list.append(items_link) if items_link else None
    url_list.append(event_url) if event_url else None
    url_list.append(ack_url) if ack_url else None
    url_list.append(host_url) if host_url else None
    
    graphs_name = body_messages_title.format(
        title=data_zabbix['title'],
        period_time=set_period_day_hour(graph_period))

    if (data_zabbix.get('settings_graphs_bool') and zabbix_graph) and trigger_settings_tag_no_graph not in zntsettings_tags[trigger_settings_tag]:
        num_items_id = [item_id for item_id in data_zabbix['itemid'].split() if re.findall(r"\d+", item_id)]
        if len(num_items_id) == 1:
            graphs_png = get_chart_png(itemid=num_items_id[0],
                                       graff_name=graphs_name,
                                       period=graph_period)
        else:
            graphs_png_group = []
            #  get the unique itemid
            for item_id in list(set([x for x in data_zabbix.get('itemid').split()])):
                if re.findall(r"\d+", item_id):
                    graphs_png_group.append(InputMediaPhoto(get_chart_png(
                        itemid=item_id,
                        graff_name=graphs_name,
                        period=graph_period).get('img')))
            graphs_png = graphs_png_group
    else:
        graphs_png = False

    subject = html.escape(args.subject.format_map(FailSafeDict(zabbix_status_emoji_map)))
    
    # Remove red severity emojis from recovery/resolved alerts
    if "Resolved" in args.subject or "OK" in args.subject:
        for red_emoji in ["🔴", "🟥"]:
            subject = subject.replace(red_emoji, "").strip()

    if body_messages_cut_symbol and len(data_zabbix['message']) > body_messages_max_symbol:
        truncated = True
        loggings.info("Message truncated to {} characters".format(body_messages_max_symbol))
    else:
        truncated = False

    body = '{} <a href="{}">...</a>'.format(
        html.escape(data_zabbix['message'])[:body_messages_max_symbol],
        zabbix_event_link.format(
            zabbix_server=zabbix_api_url, eventid=data_zabbix.get('eventid'),
            triggerid=data_zabbix.get('triggerid'))) if truncated else html.escape(data_zabbix['message'])

    links = body_messages_url_delimiter.join(url_list) if body_messages_url and len(url_list) != 0 else ''

    tags = body_messages_tags_delimiter.join(tags_list) if body_messages_tags and len(tags_list) != 0 else ''

    mentions = ' '.join(mentions) if not isinstance(mentions, bool) and body_messages_mentions_settings and len(mentions) != 0 else ''

    # Prepare reply logic
    sent_id = get_send_id(args.username)
    reply_to_message_id = None
    is_recovery = "Resolved" in args.subject or "OK" in args.subject
    
    if is_recovery:
        reply_to_message_id = get_event_cache(sent_id, data_zabbix['eventid'])
        if reply_to_message_id:
            loggings.info("Found parent message ID {} for recovery reply".format(reply_to_message_id))

    if text2image:
        # User requested pure Uzbek for generated image.
        lang = "uz"
        # Reuse enriched dictionary (includes dispatch statuses and RCA), fallback to parsing if empty.
        image_data_dict = dict(data_dict) if data_dict else {}
        if not image_data_dict:
            clean_message = data_zabbix['message'].replace('\\n', '\n')
            for line in clean_message.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    image_data_dict[k.strip()] = v.strip()
        
        if image_data_dict:
            # Determine alert type from subject if not explicitly set
            if not alert_type:
                if "Resolved" in args.subject or "OK" in args.subject:
                    alert_type = "Resolved"
                elif "Problem" in args.subject:
                    alert_type = "Problem"
                else:
                    # Try to map from emoji?
                    for severity in zabbix_status_emoji_map:
                        if severity in args.subject:
                            alert_type = severity
                            break
            
            gen_img_path = "/tmp/zbxtg_t2i_" + str(time.time()) + ".png"
            try:
                create_alert_image(image_data_dict, gen_img_path, title_text=text2image_title, alert_type=alert_type, lang=lang)
                
                # We need to send this instead of the text message if text2image is set
                # Format the caption to include tags, mentions, and buttons just like the text message does
                caption_text = body_messages.format(
                    subject=subject,
                    body="", # Body is inside the image
                    links='\n{}'.format(links) if links else '',
                    tags='\n\n{}'.format(tags) if tags else '',
                    mentions='\n{}'.format(mentions) if mentions else ''
                )
                
                sent_message_id = None
                existing_message_id = get_event_cache(sent_id, data_zabbix.get('eventid')) if data_zabbix.get('eventid') else None
                markup = gen_markup(data_zabbix['eventid']) if zabbix_keyboard and data_zabbix.get('settings_keyboard_bool') else None

                # SSOT behavior: for the same active event, update the existing Telegram card instead of creating duplicates.
                if existing_message_id and not is_recovery:
                    try:
                        with open(gen_img_path, 'rb') as photo:
                            media = InputMediaPhoto(media=photo, caption=caption_text, parse_mode="HTML")
                            bot.edit_message_media(chat_id=sent_id, message_id=existing_message_id, media=media, reply_markup=markup)
                        sent_message_id = existing_message_id
                        loggings.info('Bot updated text2image message {} for event {}.'.format(existing_message_id, data_zabbix.get('eventid')))
                    except Exception as edit_err:
                        loggings.warning("edit_message_media failed, fallback to send_photo: {}".format(edit_err))

                if not sent_message_id:
                    with open(gen_img_path, 'rb') as photo:
                        sent_msg = bot.send_photo(
                            chat_id=sent_id,
                            photo=photo,
                            caption=caption_text,
                            parse_mode="HTML",
                            reply_markup=markup,
                            reply_to_message_id=reply_to_message_id
                        )
                    sent_message_id = sent_msg.message_id
                os.remove(gen_img_path)
                loggings.info('Bot send text2image to "{}"'.format(args.username))
                
                if not is_recovery and sent_message_id:
                    set_event_cache(sent_id, data_zabbix['eventid'], sent_message_id)
                exit(0)
            except Exception as e:
                loggings.error("Text2Image failed: {}".format(e))
                # Fallback to normal message continue below

    message = body_messages.format(subject=subject, body='\n\n'+body if body else '',
                                   links='\n'+links if links else '', tags='\n\n'+tags if tags else '',
                                   mentions='\n\n'+mentions if mentions else '')

    sent_message_id = send_messages(args.username, message, graphs_png, data_zabbix['eventid'], data_zabbix.get('settings_keyboard_bool'),
                  disable_notification=True if isinstance(zntsettings_tags, dict) and trigger_settings_tag_not_notify in zntsettings_tags[trigger_settings_tag]
                  else False, reply_to_message_id=reply_to_message_id)

    if not is_recovery and sent_message_id and sent_message_id is not True:
        set_event_cache(sent_id, data_zabbix['eventid'], sent_message_id)

    exit(0)


if __name__ == "__main__":
    main()
