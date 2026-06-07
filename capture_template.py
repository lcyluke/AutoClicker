#!/usr/bin/env python3
"""
Template Capture Tool — screenshot button images as templates
模板截图工具 — 截取按钮图像保存为模板

Usage:
  python capture_template.py              # auto-detect language
  python capture_template.py --lang en    # English
  python capture_template.py --lang zh    # 中文

How it works:
  Run the script → type a template name → countdown 3s →
  move mouse to target button → screenshot auto-captured.
"""

import time
import sys
from pathlib import Path

import pyautogui
from PIL import Image

# ── i18n ───────────────────────────────────────────────────

T = {
    "en": {
        "banner_title": "Button Template Capture Tool",
        "ask_name": "Template name (e.g. accept / apply / confirm): ",
        "name_empty": "Name cannot be empty",
        "countdown": "  {}...",
        "countdown_hint": "\n3s countdown — move mouse to target button...",
        "saved": "\n✅ Template saved: {}",
        "size_coords": "   Size: {}   Coords: ({},{})-({},{})",
        "again": "\nCapture another template? (y/n): ",
        "again_name": "Template name: ",
        "done": "\nDone! Templates saved to: {}",
        "done_hint": "Restart auto_confirm.py to load new templates",
    },
    "zh": {
        "banner_title": "按钮模板截图工具",
        "ask_name": "输入模板名称（如 accept / apply / 确认）: ",
        "name_empty": "名称不能为空",
        "countdown": "  {}...",
        "countdown_hint": "\n3 秒后截取鼠标位置的按钮区域，请将鼠标移到目标按钮上...",
        "saved": "\n✅ 已保存模板: {}",
        "size_coords": "   尺寸: {}  坐标: ({},{})-({},{})",
        "again": "\n继续截取另一个模板？(y/n): ",
        "again_name": "输入模板名称: ",
        "done": "\n完成！模板已保存到: {}",
        "done_hint": "重启 auto_confirm.py 即可加载新模板",
    },
}

LANG = "en"

def detect_lang() -> str:
    args = [a for a in sys.argv[1:] if a.startswith("--lang=")]
    if args:
        lang = args[0].split("=", 1)[1].lower()
        if lang in ("zh", "cn", "chinese", "中文"):
            return "zh"
    return "en"

def t(key: str, *args) -> str:
    s = T.get(LANG, T["en"]).get(key, T["en"].get(key, key))
    if args:
        return s.format(*args)
    return s

# ── Capture ─────────────────────────────────────────────────

TEMPLATE_DIR = Path(__file__).parent / "templates"
TEMPLATE_DIR.mkdir(exist_ok=True)

CAPTURE_W = 140
CAPTURE_H = 44


def capture_around_mouse(name: str):
    print(t("countdown_hint"))
    for i in range(3, 0, -1):
        print(t("countdown", i), end="\r")
        time.sleep(1)

    mx, my = pyautogui.position()
    left   = mx - CAPTURE_W // 2
    top    = my - CAPTURE_H // 2
    right  = left + CAPTURE_W
    bottom = top + CAPTURE_H

    img = pyautogui.screenshot(region=(left, top, CAPTURE_W, CAPTURE_H))

    save_path = TEMPLATE_DIR / f"{name}.png"
    img.save(save_path)
    print(t("saved", str(save_path)))
    print(t("size_coords", img.size, left, top, right, bottom))

    img.show()


# ── Main ────────────────────────────────────────────────────

if __name__ == "__main__":
    LANG = detect_lang()

    print("=" * 40)
    print(t("banner_title"))
    print("=" * 40)

    name = input(t("ask_name")).strip()
    if not name:
        print(t("name_empty"))
        sys.exit(1)

    capture_around_mouse(name)

    again = input(t("again")).strip().lower()
    while again == "y":
        name = input(t("again_name")).strip()
        if name:
            capture_around_mouse(name)
        again = input(t("again")).strip().lower()

    print(t("done", str(TEMPLATE_DIR)))
    print(t("done_hint"))
