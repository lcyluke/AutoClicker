#!/usr/bin/env python3
"""
AutoConfirm - Auto-click IDE confirm buttons
AutoConfirm - 自动点击 IDE 确认按钮

Dual engine: image template matching + OCR text detection
Cross-platform: macOS / Windows / Linux

Usage:
  python auto_confirm.py              # defaults to English
  python auto_confirm.py --lang en    # English
  python auto_confirm.py --lang zh    # 中文

Dependencies:
  pip install pyautogui pillow pytesseract opencv-python numpy
"""

import time
import sys
import os
import platform
import subprocess
import logging
import threading
import signal
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

import pyautogui
import numpy as np
from PIL import Image, ImageGrab, ImageEnhance, ImageFilter

# ── i18n ───────────────────────────────────────────────────

T = {
    "en": {
        "ocr_unavailable": "⚠️  pytesseract not installed. OCR unavailable.",
        "template_dir_created": "Template directory created: {}",
        "template_dir_hint": "Place button screenshots (.png) in this directory. File name = button name.",
        "template_loaded": "Loading template: {}",
        "ocr_found": "[OCR] Found button: '{}' (confidence:{}%) @ ({}, {})",
        "ocr_failed": "OCR failed: {}",
        "template_found": "[Template] Found button: '{}' (match:{:.2%}) @ ({}, {})",
        "click_cooldown": "Cooldown active, skipping: {}",
        "click_ok": "✅ Clicked: [{}] @ ({}, {})  total:{}",
        "notify_title": "🤖 AutoConfirm",
        "notify_msg": "Auto-clicked: \"{}\"",
        "scan_error": "Scan error: {}",
        "start_banner": "AutoConfirm started",
        "start_interval": "  Scan interval: {}s",
        "start_ocr": "  OCR engine: {}",
        "start_template": "  Template engine: {}",
        "start_tpl_dir": "  Template dir: {}",
        "start_stop": "Press Ctrl+C to stop",
        "cli_help": "Commands: [p] pause/resume  [s] status  [q] quit",
        "cli_resumed": "▶️  Resumed",
        "cli_paused": "⏸  Paused",
        "cli_status": "Status: {} | Total clicks: {}",
        "cli_running": "running",
        "cli_paused_state": "paused",
        "cli_exiting": "Exiting...",
        "sigint_stop": "\nSignal {} received. Stopping... (total clicks: {})",
        "eng_available": "✅",
        "eng_unavailable": "❌",
    },
    "zh": {
        "ocr_unavailable": "⚠️  pytesseract 未安装，OCR不可用。",
        "template_dir_created": "已创建模板目录: {}",
        "template_dir_hint": "请将按钮截图（.png）放入该目录，文件名即为按钮名称",
        "template_loaded": "加载模板: {}",
        "ocr_found": "[OCR] 发现按钮: '{}' (置信度:{}%) @ ({}, {})",
        "ocr_failed": "OCR 失败: {}",
        "template_found": "[模板] 发现按钮: '{}' (匹配度:{:.2%}) @ ({}, {})",
        "click_cooldown": "冷却中，跳过点击: {}",
        "click_ok": "✅ 点击成功: [{}] @ ({}, {})  累计:{}次",
        "notify_title": "🤖 AutoConfirm",
        "notify_msg": "已自动点击: \"{}\"",
        "scan_error": "扫描异常: {}",
        "start_banner": "AutoConfirm 启动",
        "start_interval": "  扫描间隔: {}s",
        "start_ocr": "  OCR 引擎: {}",
        "start_template": "  模板引擎: {}",
        "start_tpl_dir": "  模板目录: {}",
        "start_stop": "按 Ctrl+C 停止",
        "cli_help": "命令: [p]暂停/恢复  [s]状态  [q]退出",
        "cli_resumed": "▶️  已恢复",
        "cli_paused": "⏸  已暂停",
        "cli_status": "状态: {} | 累计点击: {} 次",
        "cli_running": "运行中",
        "cli_paused_state": "已暂停",
        "cli_exiting": "正在退出...",
        "sigint_stop": "\n收到信号 {}，正在退出... (共点击 {} 次)",
        "eng_available": "✅",
        "eng_unavailable": "❌",
    },
}

LANG = "en"

def detect_lang() -> str:
    argv = sys.argv[1:]
    for i, a in enumerate(argv):
        if a == "--lang":
            if i + 1 < len(argv):
                lang = argv[i + 1].lower()
                if lang in ("zh", "cn", "chinese", "中文"):
                    return "zh"
            return "en"
        if a.startswith("--lang="):
            lang = a.split("=", 1)[1].lower()
            if lang in ("zh", "cn", "chinese", "中文"):
                return "zh"
            return "en"
    return "en"

def t(key: str, *args) -> str:
    s = T.get(LANG, T["en"]).get(key, T["en"].get(key, key))
    if args:
        return s.format(*args)
    return s

# ── OCR ─────────────────────────────────────────────────────

try:
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

# ── Logging ─────────────────────────────────────────────────

LOG_FILE = Path(__file__).parent / "auto_confirm.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(str(LOG_FILE), encoding="utf-8"),
    ],
)
log = logging.getLogger("AutoConfirm")

# ── Config ──────────────────────────────────────────────────

@dataclass
class Config:
    poll_interval: float = 1.2
    image_confidence: float = 0.75
    target_labels: list = field(default_factory=lambda: [
        "accept", "accept all", "apply", "apply all",
        "confirm", "yes", "ok", "run", "save", "allow",
        "continue", "proceed", "approve",
        "接受", "接受所有", "确认", "应用", "保存", "继续",
    ])
    skip_labels: list = field(default_factory=lambda: [
        "delete", "remove", "discard", "drop",
        "force", "overwrite", "reset", "cancel",
        "删除", "丢弃", "覆盖", "重置",
    ])
    click_cooldown: float = 2.0
    capture_region: Optional[tuple] = None
    template_dir: Path = Path(__file__).parent / "templates"
    use_ocr: bool = True
    use_template: bool = True
    use_notification: bool = True

CONFIG = Config()

# ── State ───────────────────────────────────────────────────

class State:
    running = True
    enabled = True
    last_click_time = 0.0
    click_count = 0

STATE = State()

# ── Cross-platform notification ──────────────────────────────

def notify(title: str, msg: str):
    """Send desktop notification. Platform-aware with console fallback."""
    if not CONFIG.use_notification:
        return

    system = platform.system()

    try:
        if system == "Darwin":
            # macOS: osascript
            os.system(
                f'osascript -e \'display notification "{msg}" with title "{title}"\''
            )
        elif system == "Windows":
            # Windows: try win10toast, fallback to ctypes popup
            try:
                from win10toast import ToastNotifier
                ToastNotifier().show_toast(title, msg, duration=3, threaded=True)
            except ImportError:
                import ctypes
                ctypes.windll.user32.MessageBoxW(0, msg, title, 0x40)
        else:
            # Linux: notify-send
            subprocess.run(
                ["notify-send", title, msg],
                capture_output=True, timeout=3
            )
    except Exception:
        pass  # notification is best-effort — log already captures it

# ── Screenshot ──────────────────────────────────────────────

def grab_screen() -> Image.Image:
    if CONFIG.capture_region:
        l, t, w, h = CONFIG.capture_region
        return ImageGrab.grab(bbox=(l, t, l + w, t + h))
    return ImageGrab.grab()

# ── Engine 1: OCR ───────────────────────────────────────────

def preprocess_for_ocr(img: Image.Image) -> Image.Image:
    img = img.convert("L")
    img = ImageEnhance.Contrast(img).enhance(2.0)
    img = img.filter(ImageFilter.SHARPEN)
    w, h = img.size
    img = img.resize((w * 2, h * 2), Image.LANCZOS)
    return img

def find_button_by_ocr(screenshot: Image.Image) -> Optional[tuple]:
    if not OCR_AVAILABLE or not CONFIG.use_ocr:
        return None

    try:
        processed = preprocess_for_ocr(screenshot)
        data = pytesseract.image_to_data(
            processed,
            output_type=pytesseract.Output.DICT,
            config="--psm 11",
            lang="eng+chi_sim",
        )
    except Exception as e:
        log.debug(t("ocr_failed", str(e)))
        return None

    n = len(data["text"])
    scale = 2

    for i in range(n):
        word = (data["text"][i] or "").strip()
        conf = int(data["conf"][i] or 0)

        if not word or conf < 50:
            continue

        word_lower = word.lower()

        if any(s in word_lower for s in CONFIG.skip_labels):
            continue

        if any(t_ in word_lower for t_ in CONFIG.target_labels):
            x = data["left"][i] / scale
            y = data["top"][i] / scale
            w = data["width"][i] / scale
            h = data["height"][i] / scale

            cx = int(x + w / 2)
            cy = int(y + h / 2)

            if CONFIG.capture_region:
                cx += CONFIG.capture_region[0]
                cy += CONFIG.capture_region[1]

            log.info(t("ocr_found", word, conf, cx, cy))
            return (cx, cy, word)

    return None

# ── Engine 2: Template matching ─────────────────────────────

def load_templates() -> dict:
    templates = {}
    if not CONFIG.template_dir.exists():
        CONFIG.template_dir.mkdir(parents=True)
        log.info(t("template_dir_created", str(CONFIG.template_dir)))
        log.info(t("template_dir_hint"))
        return templates

    for f in CONFIG.template_dir.glob("*.png"):
        img = cv2.imread(str(f), cv2.IMREAD_COLOR)
        if img is not None:
            templates[f.stem] = img
            log.info(t("template_loaded", f.stem))

    return templates

TEMPLATES = {}

def find_button_by_template(screenshot: Image.Image) -> Optional[tuple]:
    if not CV2_AVAILABLE or not CONFIG.use_template or not TEMPLATES:
        return None

    screen_np = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

    for name, template in TEMPLATES.items():
        if any(s in name.lower() for s in CONFIG.skip_labels):
            continue

        th, tw = template.shape[:2]
        sh, sw = screen_np.shape[:2]

        if tw > sw or th > sh:
            continue

        result = cv2.matchTemplate(screen_np, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val >= CONFIG.image_confidence:
            cx = max_loc[0] + tw // 2
            cy = max_loc[1] + th // 2

            if CONFIG.capture_region:
                cx += CONFIG.capture_region[0]
                cy += CONFIG.capture_region[1]

            log.info(t("template_found", name, max_val, cx, cy))
            return (cx, cy, name)

    return None

# ── Click execution ─────────────────────────────────────────

def do_click(cx: int, cy: int, label: str):
    now = time.time()
    if now - STATE.last_click_time < CONFIG.click_cooldown:
        log.debug(t("click_cooldown", label))
        return

    STATE.last_click_time = now
    STATE.click_count += 1

    pyautogui.moveTo(cx, cy, duration=0.15)
    pyautogui.click(cx, cy)

    log.info(t("click_ok", label, cx, cy, STATE.click_count))
    notify(t("notify_title"), t("notify_msg", label))

# ── Main scan loop ──────────────────────────────────────────

def scan_once():
    try:
        screenshot = grab_screen()

        result = find_button_by_template(screenshot)
        if not result:
            result = find_button_by_ocr(screenshot)

        if result:
            cx, cy, label = result
            do_click(cx, cy, label)

    except Exception as e:
        log.error(t("scan_error", str(e)), exc_info=False)

def run_loop():
    log.info("=" * 50)
    log.info(t("start_banner"))
    log.info(t("start_interval", CONFIG.poll_interval))
    log.info(t("start_ocr", t("eng_available") if OCR_AVAILABLE and CONFIG.use_ocr else t("eng_unavailable")))
    log.info(t("start_template", t("eng_available") if CV2_AVAILABLE and CONFIG.use_template else t("eng_unavailable")))
    log.info(t("start_tpl_dir", str(CONFIG.template_dir)))
    log.info(t("start_stop"))
    log.info("=" * 50)

    global TEMPLATES
    if CV2_AVAILABLE:
        TEMPLATES = load_templates()

    while STATE.running:
        if STATE.enabled:
            scan_once()
        time.sleep(CONFIG.poll_interval)

# ── CLI input listener ──────────────────────────────────────

def input_listener():
    print(f"\n{t('cli_help')}\n")
    while STATE.running:
        try:
            cmd = input().strip().lower()
            if cmd == "p":
                STATE.enabled = not STATE.enabled
                status = t("cli_resumed") if STATE.enabled else t("cli_paused")
                print(f"\n{status}\n")
            elif cmd == "s":
                status_text = t("cli_running") if STATE.enabled else t("cli_paused_state")
                print(f"\n{t('cli_status', status_text, STATE.click_count)}\n")
            elif cmd == "q":
                STATE.running = False
                print(f"\n{t('cli_exiting')}")
                break
        except (EOFError, KeyboardInterrupt):
            break

# ── Graceful exit ───────────────────────────────────────────

def handle_signal(sig, frame):
    log.info(t("sigint_stop", sig, STATE.click_count))
    STATE.running = False
    sys.exit(0)

signal.signal(signal.SIGINT, handle_signal)
signal.signal(signal.SIGTERM, handle_signal)

# ── Entry ───────────────────────────────────────────────────

if __name__ == "__main__":
    LANG = detect_lang()

    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.05

    t_ = threading.Thread(target=input_listener, daemon=True)
    t_.start()

    run_loop()
