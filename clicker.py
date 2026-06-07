#!/usr/bin/env python3
"""
AutoClicker - IDE 多 session 自动点击器
逻辑：
  点Tab1 → 在录入位置周围扫描"Run"字(最多等7s) → 找到就点 → 等3s
  点Tab2 → 同上
  点Tab3 → 同上
  回到Tab1 循环

依赖：
  pip install pyautogui pillow pytesseract opencv-python numpy
  brew install tesseract
"""

import json
import time
import sys
import signal
from pathlib import Path

import pyautogui
import numpy as np
from PIL import Image, ImageGrab, ImageEnhance, ImageFilter

# OCR
try:
    import pytesseract
    OCR_OK = True
except ImportError:
    OCR_OK = False
    print("⚠️  pytesseract 未安装，OCR识别不可用。运行: pip install pytesseract 并 brew install tesseract")

# OpenCV（可选，用于模板匹配备用）
try:
    import cv2
    CV2_OK = True
except ImportError:
    CV2_OK = False

pyautogui.FAILSAFE = True
pyautogui.PAUSE    = 0.05

BASE_DIR    = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "click_sequence.json"

# ─────────────────────────────────────────────────────────────
# 配置默认值
# ─────────────────────────────────────────────────────────────
DEFAULT_CFG = {
    "steps": [],
    "run_scan_timeout": 7,    # 最多等几秒识别Run按钮
    "run_scan_interval": 0.8, # 每次扫描间隔
    "after_run_delay": 3,     # 点击Run后等待秒数
    "after_tab_delay": 1.0,   # 点击Tab后等待秒数（等页面响应）
    "scan_width": 100,        # 扫描区域宽度(像素) - 约一个按钮宽度
    "scan_height": 36,        # 扫描区域高度(像素) - 约一个按钮高度
    "loop_delay": 2,          # 每轮结束后额外等待
}

def load_config() -> dict:
    if CONFIG_FILE.exists():
        cfg = json.loads(CONFIG_FILE.read_text())
        # 补全缺少的字段
        for k, v in DEFAULT_CFG.items():
            cfg.setdefault(k, v)
        return cfg
    return dict(DEFAULT_CFG)

def save_config(cfg: dict):
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2, ensure_ascii=False))
    print(f"✅ 已保存: {CONFIG_FILE}")

# ─────────────────────────────────────────────────────────────
# OCR 识别 Run 按钮
# ─────────────────────────────────────────────────────────────

def preprocess(img: Image.Image) -> Image.Image:
    """增强图像提升OCR准确率"""
    img = img.convert("L")                         # 灰度
    img = ImageEnhance.Contrast(img).enhance(2.5)  # 高对比度
    img = img.filter(ImageFilter.SHARPEN)          # 锐化
    w, h = img.size
    img = img.resize((w * 3, h * 3), Image.LANCZOS)  # 放大3倍
    return img

def ocr_has_run(img: Image.Image) -> tuple:
    """
    在图像中用OCR查找"Run"字样
    返回 (found: bool, center_x: int, center_y: int)
    坐标是相对于传入img的局部坐标
    """
    if not OCR_OK:
        return False, 0, 0

    try:
        processed = preprocess(img)
        scale = 3  # 对应resize倍数

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

            # 匹配 "Run"（不区分大小写）
            if word.lower() in ("run", "run>", ">run", "► run"):
                # 换算回原始坐标
                x = data["left"][i] / scale + data["width"][i] / scale / 2
                y = data["top"][i] / scale + data["height"][i] / scale / 2
                print(f"    [OCR] 找到Run按钮: '{word}' 置信度:{conf}% 局部坐标:({int(x)},{int(y)})")
                return True, int(x), int(y)

        return False, 0, 0

    except Exception as e:
        print(f"    [OCR] 异常: {e}")
        return False, 0, 0

def scan_run_button(center_x: int, center_y: int, scan_w: int, scan_h: int) -> tuple:
    """
    截取 center 周围精确矩形区域（按钮大小）
    用OCR扫描是否有Run文字
    返回 (found, abs_click_x, abs_click_y)

    原理示意：
        录入坐标 (center_x, center_y) = Run按钮中心
        截图区域:
          ┌──────────┐
          │  ▶ Run   │  ← scan_width × scan_height 像素，刚好一个按钮大小
          └──────────┘
        只在这小区域做OCR，不会误识别其他文字
    """
    left = center_x - scan_w // 2
    top  = center_y - scan_h // 2

    # 截图：只截按钮大小的区域
    img = pyautogui.screenshot(region=(left, top, scan_w, scan_h))

    found, lx, ly = ocr_has_run(img)
    if found:
        # 局部坐标 → 全局坐标
        abs_x = left + lx
        abs_y = top  + ly
        return True, abs_x, abs_y

    return False, 0, 0

# ─────────────────────────────────────────────────────────────
# 核心：等待并点击 Run 按钮
# ─────────────────────────────────────────────────────────────

def wait_and_click_run(run_x: int, run_y: int, cfg: dict, step_label: str) -> bool:
    """
    在 run_x/run_y 为中心，截取 scan_width × scan_height 的小区域
    每隔一段时间OCR扫描一次，最多等 run_scan_timeout 秒
    找到Run就点击，返回True；超时返回False
    """
    timeout  = cfg["run_scan_timeout"]     # 最多等7秒
    interval = cfg["run_scan_interval"]    # 0.8秒扫一次
    scan_w   = cfg["scan_width"]           # 100px
    scan_h   = cfg["scan_height"]          # 36px

    deadline = time.time() + timeout
    attempt  = 0

    while time.time() < deadline:
        attempt += 1
        remaining = deadline - time.time()
        print(f"    扫描Run... 第{attempt}次 (剩余{remaining:.1f}s) 区域:{scan_w}×{scan_h}px", end="\r", flush=True)

        found, abs_x, abs_y = scan_run_button(run_x, run_y, scan_w, scan_h)

        if found:
            print(f"\n    ✅ [{step_label}] 找到Run，点击 ({abs_x}, {abs_y})")
            pyautogui.moveTo(abs_x, abs_y, duration=0.15)
            pyautogui.click()
            return True

        time.sleep(interval)

    print(f"\n    ⏰ [{step_label}] {timeout}秒内未找到Run按钮，跳过")
    return False

# ─────────────────────────────────────────────────────────────
# 主循环
# ─────────────────────────────────────────────────────────────

running     = True
round_count = 0

def run_loop():
    global running, round_count

    cfg = load_config()
    steps = cfg["steps"]

    if not steps:
        print("❌ 没有录制步骤，请先选 1 录制")
        return

    after_run_delay = cfg["after_run_delay"]   # 点Run后等3秒
    after_tab_delay = cfg["after_tab_delay"]   # 点Tab后等1秒
    loop_delay      = cfg["loop_delay"]

    print("\n" + "="*50)
    print(f"▶️  开始循环  共 {len(steps)} 个标签页")
    print(f"   Run识别超时: {cfg['run_scan_timeout']}s")
    print(f"   点Run后等待: {after_run_delay}s")
    print(f"   扫描区域:    {cfg['scan_width']}×{cfg['scan_height']}px")
    print("   鼠标移到屏幕左上角 = 紧急停止")
    print("   Ctrl+C = 退出")
    print("="*50)
    print("\n⏳ 3秒后开始，请切换到目标窗口...")
    time.sleep(3)

    while running:
        round_count += 1
        now = time.strftime("%H:%M:%S")
        print(f"\n{'━'*50}")
        print(f"🔄 第 {round_count} 轮  [{now}]  共{len(steps)}个标签")
        print(f"{'━'*50}")

        run_clicked = 0

        for i, step in enumerate(steps):
            if not running:
                break

            label   = step["label"]
            tab_pos = step["tab_pos"]
            run_pos = step["run_pos"]

            print(f"\n  [{i+1}/{len(steps)}] ── {label} ──")

            # ① 点击标签页
            print(f"  → 点击标签: ({tab_pos[0]}, {tab_pos[1]})")
            pyautogui.moveTo(tab_pos[0], tab_pos[1], duration=0.2)
            pyautogui.click()
            time.sleep(after_tab_delay)

            # ② 等待并识别 Run 按钮
            found = wait_and_click_run(run_pos[0], run_pos[1], cfg, label)

            if found:
                run_clicked += 1
                # ③ 点Run后等待
                print(f"  ⏳ 等待 {after_run_delay}s 后进入下一个标签...")
                for t in range(int(after_run_delay), 0, -1):
                    print(f"\r     {t}s... ", end="", flush=True)
                    time.sleep(1)
                print()

        # 一轮结束
        print(f"\n{'─'*50}")
        print(f"  本轮结束: 点击了 {run_clicked}/{len(steps)} 个Run按钮")

        if loop_delay > 0:
            print(f"  等待 {loop_delay}s 后重新从第1个标签开始...")
            time.sleep(loop_delay)

    print(f"\n🏁 已停止，共执行 {round_count} 轮")

# ─────────────────────────────────────────────────────────────
# 录制模式
# ─────────────────────────────────────────────────────────────

def countdown_get_pos(prompt: str) -> tuple:
    print(f"\n  👉 {prompt}")
    for i in range(4, 0, -1):
        print(f"\r     倒计时 {i}s，请将鼠标移到目标位置...", end="", flush=True)
        time.sleep(1)
    x, y = pyautogui.position()
    print(f"\r     ✅ 已记录坐标: ({x}, {y})              ")
    return x, y

def record_mode():
    print("\n" + "="*50)
    print("📍 录制模式")
    print("="*50)
    print("说明：")
    print("  录制时只需把鼠标【静止放在目标位置】等4秒")
    print("  不需要画圈，不需要点击，脚本自动记录坐标")

    cfg = load_config()

    try:
        n = int(input("录制几个标签页？(2-10): ").strip() or "3")
    except ValueError:
        n = 3

    steps = []
    for i in range(n):
        print(f"\n─── 第 {i+1}/{n} 个标签 ───")
        label = input(f"  标签名称（如 Task{i+1}）: ").strip() or f"Tab{i+1}"

        tab_x, tab_y = countdown_get_pos(f"移到「{label}」的标签点击位置（等4秒）")
        run_x, run_y = countdown_get_pos(f"移到「{label}」的Run按钮正中心（等4秒）")

        steps.append({
            "label": label,
            "tab_pos": [tab_x, tab_y],
            "run_pos": [run_x, run_y],
        })

    cfg["steps"] = steps

    print("\n─── 时间配置（直接回车用默认值）───")
    try:
        v = input(f"  Run识别超时秒数（默认{cfg['run_scan_timeout']}s，范围3-7）: ").strip()
        if v:
            cfg["run_scan_timeout"] = max(3, min(7, float(v)))

        v = input(f"  点击Run后等待秒数（默认{cfg['after_run_delay']}s）: ").strip()
        if v:
            cfg["after_run_delay"] = float(v)

        v = input(f"  Run扫描区域宽度像素（默认{cfg['scan_width']}px，约一个按钮宽）: ").strip()
        if v:
            cfg["scan_width"] = int(v)

        v = input(f"  Run扫描区域高度像素（默认{cfg['scan_height']}px，约一个按钮高）: ").strip()
        if v:
            cfg["scan_height"] = int(v)
    except ValueError:
        pass

    save_config(cfg)

# ─────────────────────────────────────────────────────────────
# 查看配置
# ─────────────────────────────────────────────────────────────

def show_config():
    cfg = load_config()
    print("\n" + "="*50)
    print("📋 当前配置")
    print("="*50)

    if not cfg["steps"]:
        print("  （空，还没有录制步骤）")
    else:
        for i, s in enumerate(cfg["steps"]):
            tp, rp = s["tab_pos"], s["run_pos"]
            print(f"  {i+1}. {s['label']}")
            print(f"     标签位置: ({tp[0]}, {tp[1]})")
            print(f"     Run中心:  ({rp[0]}, {rp[1]})  扫描区域:{cfg['scan_width']}×{cfg['scan_height']}px")

    print(f"\n  Run识别超时: {cfg['run_scan_timeout']}s")
    print(f"  点Run后等待: {cfg['after_run_delay']}s")
    print(f"  点Tab后等待: {cfg['after_tab_delay']}s")
    print(f"  扫描间隔:    {cfg['run_scan_interval']}s")
    print(f"  扫描区域:    {cfg['scan_width']}×{cfg['scan_height']}px")
    print(f"  OCR引擎:     {'✅ 可用' if OCR_OK else '❌ 未安装'}")

# ─────────────────────────────────────────────────────────────
# 调试：测试单点 Run 识别
# ─────────────────────────────────────────────────────────────

def test_scan():
    cfg = load_config()
    print("\n📸 测试Run按钮识别")
    print(f"   扫描区域: {cfg['scan_width']}×{cfg['scan_height']} 像素（约一个按钮大小）")
    print("   把鼠标放到Run按钮正中间就行，不用画圈或点击")
    x, y = countdown_get_pos("移到Run按钮正中间（等4秒）")

    scan_w = cfg["scan_width"]
    scan_h = cfg["scan_height"]

    print(f"\n在 ({x}, {y}) 周围截取 {scan_w}×{scan_h}px 区域...")

    # 保存截图方便调试
    left = x - scan_w // 2
    top  = y - scan_h // 2
    debug_img = pyautogui.screenshot(region=(left, top, scan_w, scan_h))
    debug_path = BASE_DIR / "debug_scan.png"
    debug_img.save(debug_path)
    print(f"  截图已保存: {debug_path}（可打开查看扫描范围是否正确）")

    found, ax, ay = scan_run_button(x, y, scan_w, scan_h)
    if found:
        print(f"✅ 识别成功！Run按钮在全局坐标: ({ax}, {ay})")
    else:
        print("❌ 未识别到Run文字")
        print("  调试建议：")
        print(f"  1. 打开 {debug_path} 看截图是否包含完整的Run按钮")
        print(f"  2. 如果按钮被截断，增大 scan_width/scan_height")
        print(f"  3. 如果按钮占比太小在截图里只占一小部分，减小 scan_width/scan_height")
        print(f"  4. 确认 brew install tesseract 已完成")

# ─────────────────────────────────────────────────────────────
# 信号
# ─────────────────────────────────────────────────────────────

def handle_exit(sig, frame):
    global running
    running = False
    print(f"\n\n⏹ 已停止，共执行 {round_count} 轮")
    sys.exit(0)

signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)

# ─────────────────────────────────────────────────────────────
# 主菜单
# ─────────────────────────────────────────────────────────────

def main():
    print("\n" + "█"*50)
    print("  AutoClicker")
    print("  标签页循环点击 + OCR识别Run按钮")
    print("  录制：鼠标放到目标位置静止等4秒即可")
    print("█"*50)

    if not OCR_OK:
        print("\n⚠️  OCR未就绪，请先安装依赖：")
        print("   pip install pytesseract")
        print("   brew install tesseract")

    while True:
        print("\n选择操作：")
        print("  1. 📍 录制点击序列（鼠标放到位置等4秒）")
        print("  2. 🔍 测试Run按钮识别（调试用）")
        print("  3. ▶️  开始循环运行")
        print("  4. 📋 查看当前配置")
        print("  5. 🚪 退出")

        choice = input("\n请输入 (1-5): ").strip()

        if   choice == "1": record_mode()
        elif choice == "2": test_scan()
        elif choice == "3": run_loop()
        elif choice == "4": show_config()
        elif choice == "5": print("再见！"); break
        else: print("请输入 1-5")

if __name__ == "__main__":
    main()
