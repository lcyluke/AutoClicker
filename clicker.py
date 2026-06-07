#!/usr/bin/env python3
"""
AutoClicker - IDE multi-session auto clicker
AutoClicker - IDE 多 session 自动点击器

Logic:
  Click Tab1 → scan around saved position for "Run" text (up to 7s) → click if found → wait 3s
  Click Tab2 → same
  Click Tab3 → same
  Back to Tab1, loop

Usage:
  python clicker.py              # auto-detect language from system
  python clicker.py --lang en    # English
  python clicker.py --lang zh    # 中文

Dependencies:
  pip install pyautogui pillow pytesseract opencv-python numpy
  brew install tesseract
"""

import json
import time
import sys
import signal
import locale
from pathlib import Path

import pyautogui
import numpy as np
from PIL import Image, ImageGrab, ImageEnhance, ImageFilter

# ── i18n ───────────────────────────────────────────────────

T = {
    "en": {
        "ocr_warn": "⚠️  pytesseract not installed. OCR unavailable. Run: pip install pytesseract && brew install tesseract",
        "cfg_saved": "✅ Saved: {}",
        "loop_start": "▶️  Starting loop  {} tabs",
        "run_timeout": "   Run detection timeout: {}s",
        "after_run_delay": "   After-run delay: {}s",
        "scan_area": "   Scan area: {}×{}px",
        "failsafe_hint": "   Mouse to top-left corner = emergency stop",
        "ctrl_c_hint": "   Ctrl+C = exit",
        "switch_hint": "⏳ Starting in 3s, switch to target window...",
        "round_header": "🔄 Round {}  [{}]  total {} tabs",
        "click_tab": "  → Click tab: ({}, {})",
        "scanning": "    Scanning Run... attempt {} (remaining {:.1f}s) area:{}×{}px",
        "found_run": "\n    ✅ [{}] Run found, click ({}, {})",
        "timeout_run": "\n    ⏰ [{}] Run not found within {}s, skipping",
        "wait_next": "  ⏳ Waiting {}s before next tab...",
        "round_end": "   Round complete: clicked {}/{} Run buttons",
        "loop_delay_wait": "   Waiting {}s before restarting from tab 1...",
        "stopped": "\n🏁 Stopped. {} rounds completed",
        "record_title": "📍 Record Mode",
        "record_hint1": "  Just hold mouse still on target for 4s — no click, no circling",
        "record_hint2": "  Coordinates are auto-captured",
        "ask_tab_count": "How many tabs? (2-10): ",
        "step_header": "─── Tab {}/{} ───",
        "ask_label": "  Tab name (e.g. Task{}): ",
        "goto_tab": "Move to [{}] tab click position (wait 5s)",
        "goto_run": "Move to [{}] Run button center (wait 7s)",
        "countdown": "      Countdown {}s, move mouse to target...",
        "recorded_pos": "\r     ✅ Position recorded: ({}, {})              ",
        "time_config_title": "─── Timing (press Enter for defaults) ───",
        "ask_timeout": "  Run detection timeout (default {}s, range 3-7): ",
        "ask_after_run": "  After-run delay (default {}s): ",
        "ask_scan_w": "  Scan width px (default {}, ~1 button wide): ",
        "ask_scan_h": "  Scan height px (default {}, ~1 button tall): ",
        "config_title": "📋 Current Config",
        "config_empty": "  (empty, no steps recorded)",
        "config_step_line": "  {}. {}",
        "config_tab_pos": "     Tab position: ({}, {})",
        "config_run_pos": "     Run center:  ({}, {})  scan area:{}×{}px",
        "config_timeout": "  Run detection timeout: {}s",
        "config_after_run": "  After-run delay: {}s",
        "config_after_tab": "  After-tab delay: {}s",
        "config_interval": "  Scan interval: {}s",
        "config_area": "  Scan area: {}×{}px",
        "config_ocr": "  OCR engine:     {}",
        "test_title": "📸 Button Capture & Recognition",
        "test_hint1": "   Scan area: {}×{} px (~one button size)",
        "test_hint2": "   Place mouse on center of target button",
        "test_goto": "Move to target button center (wait 4s)",
        "test_capture": "\nCapturing {}×{}px area around ({}, {})...",
        "test_saved": "  Screenshot saved: {} (open to verify scan area)",
        "test_success": "✅ Detected! Run button at global coords: ({}, {})",
        "test_fail": "❌ Run text not detected",
        "test_debug1": "  1. Open {} to check if screenshot includes full target button",
        "test_debug2": "  2. If button is clipped, increase scan_width/scan_height",
        "test_debug3": "  3. If button is too small, decrease scan_width/scan_height",
        "test_debug4": "  4. Confirm 'brew install tesseract' is done",
        "banner_title": "  AutoClicker",
        "banner_sub": "  Tab cycle clicker + OCR Run button detection",
        "banner_hint": "  Record: hold mouse still on target for 5s",
        "menu_title": "Choose action:",
        "menu_1": "  1. 📍 Record click sequence (hold mouse still 4s)",
        "menu_2": "  2. 🔍 Capture & Recognize Buttons",
        "menu_3": "  3. ▶️  Start loop",
        "menu_4": "  4. 📋 View current config",
        "menu_5": "  5. 🚪 Exit",
        "menu_prompt": "\nEnter choice (1-5): ",
        "menu_invalid": "Enter 1-5",
        "bye": "Goodbye!",
        "ocr_ready": "✅ available",
        "ocr_not_ready": "❌ not installed",
        "no_steps": "❌ No steps recorded. Please choose 1 to record first.",
        "sigint_stop": "\n\n⏹ Stopped. {} rounds completed",
        "ocr_found": "    [OCR] Run button found: '{}' confidence:{}% local:({},{})",
        "ocr_error": "    [OCR] error: {}",
    },
    "zh": {
        "ocr_warn": "⚠️  pytesseract 未安装，OCR识别不可用。运行: pip install pytesseract 并 brew install tesseract",
        "cfg_saved": "✅ 已保存: {}",
        "loop_start": "▶️  开始循环  共 {} 个标签页",
        "run_timeout": "   Run识别超时: {}s",
        "after_run_delay": "   点Run后等待: {}s",
        "scan_area": "   扫描区域:    {}×{}px",
        "failsafe_hint": "   鼠标移到屏幕左上角 = 紧急停止",
        "ctrl_c_hint": "   Ctrl+C = 退出",
        "switch_hint": "⏳ 3秒后开始，请切换到目标窗口...",
        "round_header": "🔄 第 {} 轮  [{}]  共{}个标签",
        "click_tab": "  → 点击标签: ({}, {})",
        "scanning": "    扫描Run... 第{}次 (剩余{:.1f}s) 区域:{}×{}px",
        "found_run": "\n    ✅ [{}] 找到Run，点击 ({}, {})",
        "timeout_run": "\n    ⏰ [{}] {}秒内未找到Run按钮，跳过",
        "wait_next": "  ⏳ 等待 {}s 后进入下一个标签...",
        "round_end": "  本轮结束: 点击了 {}/{} 个Run按钮",
        "loop_delay_wait": "  等待 {}s 后重新从第1个标签开始...",
        "stopped": "\n🏁 已停止，共执行 {} 轮",
        "record_title": "📍 录制模式",
        "record_hint1": "  录制时只需把鼠标【静止放在目标位置】等4秒",
        "record_hint2": "  不需要画圈，不需要点击，脚本自动记录坐标",
        "ask_tab_count": "录制几个标签页？(2-10): ",
        "step_header": "─── 第 {}/{} 个标签 ───",
        "ask_label": "  标签名称（如 Task{}）: ",
        "goto_tab": "移到「{}」的标签点击位置（等5秒）",
        "goto_run": "移到「{}」的Run按钮正中心（等7秒）",
        "countdown": "     倒计时 {}s，请将鼠标移到目标位置...",
        "recorded_pos": "\r     ✅ 已记录坐标: ({}, {})              ",
        "time_config_title": "─── 时间配置（直接回车用默认值）───",
        "ask_timeout": "  Run识别超时秒数（默认{}s，范围3-7）: ",
        "ask_after_run": "  点击Run后等待秒数（默认{}s）: ",
        "ask_scan_w": "  Run扫描区域宽度像素（默认{}px，约一个按钮宽）: ",
        "ask_scan_h": "  Run扫描区域高度像素（默认{}px，约一个按钮高）: ",
        "config_title": "📋 当前配置",
        "config_empty": "  （空，还没有录制步骤）",
        "config_step_line": "  {}. {}",
        "config_tab_pos": "     标签位置: ({}, {})",
        "config_run_pos": "     Run中心:  ({}, {})  扫描区域:{}×{}px",
        "config_timeout": "  Run识别超时: {}s",
        "config_after_run": "  点Run后等待: {}s",
        "config_after_tab": "  点Tab后等待: {}s",
        "config_interval": "  扫描间隔:    {}s",
        "config_area": "  扫描区域:    {}×{}px",
        "config_ocr": "  OCR引擎:     {}",
        "test_title": "📸 按钮识别采集",
        "test_hint1": "   扫描区域: {}×{} 像素（约一个按钮大小）",
        "test_hint2": "   把鼠标放到目标按钮正中间就行，不用画圈或点击",
        "test_goto": "移到目标按钮正中间（等4秒）",
        "test_capture": "\n在 ({}, {}) 周围截取 {}×{}px 区域...",
        "test_saved": "  截图已保存: {}（可打开查看扫描范围是否正确）",
        "test_success": "✅ 识别成功！Run按钮在全局坐标: ({}, {})",
        "test_fail": "❌ 未识别到Run文字",
        "test_debug1": "  1. 打开 {} 看截图是否包含完整的目标按钮",
        "test_debug2": "  2. 如果按钮被截断，增大 scan_width/scan_height",
        "test_debug3": "  3. 如果按钮占比太小，减小 scan_width/scan_height",
        "test_debug4": "  4. 确认 brew install tesseract 已完成",
        "banner_title": "  AutoClicker",
        "banner_sub": "  标签页循环点击 + OCR识别Run按钮",
        "banner_hint": "  录制：鼠标放到目标位置静止等5秒即可",
        "menu_title": "选择操作：",
        "menu_1": "  1. 📍 录制点击序列（鼠标放到位置等4秒）",
        "menu_2": "  2. 🔍 按钮图标识别采集",
        "menu_3": "  3. ▶️  开始循环运行",
        "menu_4": "  4. 📋 查看当前配置",
        "menu_5": "  5. 🚪 退出",
        "menu_prompt": "\n请输入 (1-5): ",
        "menu_invalid": "请输入 1-5",
        "bye": "再见！",
        "ocr_ready": "✅ 可用",
        "ocr_not_ready": "❌ 未安装",
        "no_steps": "❌ 没有录制步骤，请先选 1 录制",
        "sigint_stop": "\n\n⏹ 已停止，共执行 {} 轮",
        "ocr_found": "    [OCR] 找到Run按钮: '{}' 置信度:{}% 局部坐标:({},{})",
        "ocr_error": "    [OCR] 异常: {}",
    },
}

LANG = "en"

def detect_lang() -> str:
    """Detect language from --lang flag or system locale."""
    args = [a for a in sys.argv[1:] if a.startswith("--lang=")]
    if args:
        lang = args[0].split("=", 1)[1]
        if lang in ("zh", "cn", "chinese", "中文"):
            return "zh"
        return "en"

    try:
        sl = locale.getdefaultlocale()[0] or ""
        if sl.startswith("zh"):
            return "zh"
    except Exception:
        pass
    return "en"

def t(key: str, *args) -> str:
    """Look up translated string. Call as t('key', arg1, arg2, ...)."""
    s = T.get(LANG, T["en"]).get(key, T["en"].get(key, key))
    if args:
        return s.format(*args)
    return s

# ── OCR ─────────────────────────────────────────────────────

try:
    import pytesseract
    OCR_OK = True
except ImportError:
    OCR_OK = False
    print(t("ocr_warn"))

try:
    import cv2
    CV2_OK = True
except ImportError:
    CV2_OK = False

pyautogui.FAILSAFE = True
pyautogui.PAUSE    = 0.05

BASE_DIR    = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "click_sequence.json"

# ── Default config ──────────────────────────────────────────

DEFAULT_CFG = {
    "steps": [],
    "run_scan_timeout": 7,
    "run_scan_interval": 0.8,
    "after_run_delay": 3,
    "after_tab_delay": 1.0,
    "scan_width": 100,
    "scan_height": 36,
    "loop_delay": 2,
}

def load_config() -> dict:
    if CONFIG_FILE.exists():
        cfg = json.loads(CONFIG_FILE.read_text())
        for k, v in DEFAULT_CFG.items():
            cfg.setdefault(k, v)
        return cfg
    return dict(DEFAULT_CFG)

def save_config(cfg: dict):
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2, ensure_ascii=False))
    print(t("cfg_saved", str(CONFIG_FILE)))

# ── OCR Run button detection ────────────────────────────────

def preprocess(img: Image.Image) -> Image.Image:
    """Enhance image for better OCR accuracy."""
    img = img.convert("L")
    img = ImageEnhance.Contrast(img).enhance(2.5)
    img = img.filter(ImageFilter.SHARPEN)
    w, h = img.size
    img = img.resize((w * 3, h * 3), Image.LANCZOS)
    return img

def ocr_has_run(img: Image.Image) -> tuple:
    """
    OCR scan for "Run" text in image.
    Returns (found: bool, center_x: int, center_y: int)
    Coordinates relative to input image.
    """
    if not OCR_OK:
        return False, 0, 0

    try:
        processed = preprocess(img)
        scale = 3

        data = pytesseract.image_to_data(
            processed,
            output_type=pytesseract.Output.DICT,
            config="--psm 11 -c tessedit_char_whitelist=RunBTNbtn",
        )

        for i, word in enumerate(data["text"]):
            word = (word or "").strip()
            conf = int(data["conf"][i] or 0)

            if conf < 40:
                continue

            if word.lower() in ("run", "run>", ">run", "► run"):
                x = data["left"][i] / scale + data["width"][i] / scale / 2
                y = data["top"][i] / scale + data["height"][i] / scale / 2
                print(t("ocr_found", word, conf, int(x), int(y)))
                return True, int(x), int(y)

        return False, 0, 0

    except Exception as e:
        print(t("ocr_error", str(e)))
        return False, 0, 0

def scan_run_button(center_x: int, center_y: int, scan_w: int, scan_h: int) -> tuple:
    """
    Screenshot a small rectangle around center and OCR-scan for "Run".
    Returns (found, abs_click_x, abs_click_y).
    """
    left = center_x - scan_w // 2
    top  = center_y - scan_h // 2

    img = pyautogui.screenshot(region=(left, top, scan_w, scan_h))

    found, lx, ly = ocr_has_run(img)
    if found:
        abs_x = left + lx
        abs_y = top  + ly
        return True, abs_x, abs_y

    return False, 0, 0

# ── Core: wait and click Run ────────────────────────────────

def wait_and_click_run(run_x: int, run_y: int, cfg: dict, step_label: str) -> bool:
    """
    Center on run_x/run_y, screenshot scan_width × scan_height,
    OCR every interval, timeout after run_scan_timeout seconds.
    Clicks Run if found.
    """
    timeout  = cfg["run_scan_timeout"]
    interval = cfg["run_scan_interval"]
    scan_w   = cfg["scan_width"]
    scan_h   = cfg["scan_height"]

    deadline = time.time() + timeout
    attempt  = 0

    while time.time() < deadline:
        attempt += 1
        remaining = deadline - time.time()
        print(t("scanning", attempt, remaining, scan_w, scan_h), end="\r", flush=True)

        found, abs_x, abs_y = scan_run_button(run_x, run_y, scan_w, scan_h)

        if found:
            print(t("found_run", step_label, abs_x, abs_y))
            pyautogui.moveTo(abs_x, abs_y, duration=0.15)
            pyautogui.click()
            return True

        time.sleep(interval)

    print(t("timeout_run", step_label, timeout))
    return False

# ── Main loop ───────────────────────────────────────────────

running     = True
round_count = 0

def run_loop():
    global running, round_count

    cfg = load_config()
    steps = cfg["steps"]

    if not steps:
        print(t("no_steps"))
        return

    after_run_delay = cfg["after_run_delay"]
    after_tab_delay = cfg["after_tab_delay"]
    loop_delay      = cfg["loop_delay"]

    print("\n" + "="*50)
    print(t("loop_start", len(steps)))
    print(t("run_timeout", cfg["run_scan_timeout"]))
    print(t("after_run_delay", after_run_delay))
    print(t("scan_area", cfg["scan_width"], cfg["scan_height"]))
    print(t("failsafe_hint"))
    print(t("ctrl_c_hint"))
    print("="*50)
    print(t("switch_hint"))
    time.sleep(3)

    while running:
        round_count += 1
        now = time.strftime("%H:%M:%S")
        print(f"\n{'━'*50}")
        print(t("round_header", round_count, now, len(steps)))
        print(f"{'━'*50}")

        run_clicked = 0

        for i, step in enumerate(steps):
            if not running:
                break

            label   = step["label"]
            tab_pos = step["tab_pos"]
            run_pos = step["run_pos"]

            print(f"\n  [{i+1}/{len(steps)}] ── {label} ──")

            print(t("click_tab", tab_pos[0], tab_pos[1]))
            pyautogui.moveTo(tab_pos[0], tab_pos[1], duration=0.2)
            pyautogui.click()
            time.sleep(after_tab_delay)

            found = wait_and_click_run(run_pos[0], run_pos[1], cfg, label)

            if found:
                run_clicked += 1
                print(t("wait_next", after_run_delay))
                for t_ in range(int(after_run_delay), 0, -1):
                    print(f"\r     {t_}s... ", end="", flush=True)
                    time.sleep(1)
                print()

        print(f"\n{'─'*50}")
        print(t("round_end", run_clicked, len(steps)))

        if loop_delay > 0:
            print(t("loop_delay_wait", loop_delay))
            time.sleep(loop_delay)

    print(t("stopped", round_count))

# ── Record mode ─────────────────────────────────────────────

def countdown_get_pos(prompt: str, seconds: int = 4) -> tuple:
    print(f"\n  👉 {prompt}")
    for i in range(seconds, 0, -1):
        print(t("countdown", i), end="", flush=True)
        time.sleep(1)
    x, y = pyautogui.position()
    print(t("recorded_pos", x, y))
    return x, y

def record_mode():
    print("\n" + "="*50)
    print(t("record_title"))
    print("="*50)
    print(t("record_hint1"))
    print(t("record_hint2"))

    cfg = load_config()

    try:
        n = int(input(t("ask_tab_count")).strip() or "3")
    except ValueError:
        n = 3

    steps = []
    for i in range(n):
        print(t("step_header", i+1, n))
        label = input(t("ask_label", i+1)).strip() or f"Tab{i+1}"

        tab_x, tab_y = countdown_get_pos(t("goto_tab", label), seconds=5)
        run_x, run_y = countdown_get_pos(t("goto_run", label), seconds=7)

        steps.append({
            "label": label,
            "tab_pos": [tab_x, tab_y],
            "run_pos": [run_x, run_y],
        })

    cfg["steps"] = steps

    print(t("time_config_title"))
    try:
        v = input(t("ask_timeout", cfg["run_scan_timeout"])).strip()
        if v:
            cfg["run_scan_timeout"] = max(3, min(7, float(v)))

        v = input(t("ask_after_run", cfg["after_run_delay"])).strip()
        if v:
            cfg["after_run_delay"] = float(v)

        v = input(t("ask_scan_w", cfg["scan_width"])).strip()
        if v:
            cfg["scan_width"] = int(v)

        v = input(t("ask_scan_h", cfg["scan_height"])).strip()
        if v:
            cfg["scan_height"] = int(v)
    except ValueError:
        pass

    save_config(cfg)

# ── Show config ─────────────────────────────────────────────

def show_config():
    cfg = load_config()
    print("\n" + "="*50)
    print(t("config_title"))
    print("="*50)

    if not cfg["steps"]:
        print(t("config_empty"))
    else:
        for i, s in enumerate(cfg["steps"]):
            tp, rp = s["tab_pos"], s["run_pos"]
            print(t("config_step_line", i+1, s["label"]))
            print(t("config_tab_pos", tp[0], tp[1]))
            print(t("config_run_pos", rp[0], rp[1], cfg["scan_width"], cfg["scan_height"]))

    print(t("config_timeout", cfg["run_scan_timeout"]))
    print(t("config_after_run", cfg["after_run_delay"]))
    print(t("config_after_tab", cfg["after_tab_delay"]))
    print(t("config_interval", cfg["run_scan_interval"]))
    print(t("config_area", cfg["scan_width"], cfg["scan_height"]))
    print(t("config_ocr", t("ocr_ready") if OCR_OK else t("ocr_not_ready")))

# ── Test scan ───────────────────────────────────────────────

def test_scan():
    cfg = load_config()
    print(t("test_title"))
    print(t("test_hint1", cfg["scan_width"], cfg["scan_height"]))
    print(t("test_hint2"))
    x, y = countdown_get_pos(t("test_goto"))

    scan_w = cfg["scan_width"]
    scan_h = cfg["scan_height"]

    print(t("test_capture", x, y, scan_w, scan_h))

    left = x - scan_w // 2
    top  = y - scan_h // 2
    debug_img = pyautogui.screenshot(region=(left, top, scan_w, scan_h))
    debug_path = BASE_DIR / "debug_scan.png"
    debug_img.save(debug_path)
    print(t("test_saved", str(debug_path)))

    found, ax, ay = scan_run_button(x, y, scan_w, scan_h)
    if found:
        print(t("test_success", ax, ay))
    else:
        print(t("test_fail"))
        print(t("test_debug1", str(debug_path)))
        print(t("test_debug2"))
        print(t("test_debug3"))
        print(t("test_debug4"))

# ── Signal handlers ─────────────────────────────────────────

def handle_exit(sig, frame):
    global running
    running = False
    print(t("sigint_stop", round_count))
    sys.exit(0)

signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)

# ── Main menu ───────────────────────────────────────────────

def main():
    print("\n" + "█"*50)
    print(t("banner_title"))
    print(t("banner_sub"))
    print(t("banner_hint"))
    print("█"*50)

    if not OCR_OK:
        print(t("ocr_warn"))
        print("   pip install pytesseract")
        print("   brew install tesseract")

    while True:
        print(f"\n{t('menu_title')}")
        print(t("menu_1"))
        print(t("menu_2"))
        print(t("menu_3"))
        print(t("menu_4"))
        print(t("menu_5"))

        choice = input(t("menu_prompt")).strip()

        if   choice == "1": record_mode()
        elif choice == "2": test_scan()
        elif choice == "3": run_loop()
        elif choice == "4": show_config()
        elif choice == "5": print(t("bye")); break
        else: print(t("menu_invalid"))

if __name__ == "__main__":
    LANG = detect_lang()
    main()
