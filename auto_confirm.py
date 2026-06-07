#!/usr/bin/env python3
"""
AutoConfirm - 自动点击 Kiro/VSCode 确认按钮
双引擎：图像模板匹配 + OCR 文字识别
macOS 专用

依赖安装：
    pip install pyautogui pillow pytesseract opencv-python numpy
    brew install tesseract
"""

import time
import sys
import os
import logging
import threading
import signal
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

import pyautogui
import numpy as np
from PIL import Image, ImageGrab, ImageEnhance, ImageFilter

# OCR 是可选依赖，没装也能用图像模式
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

# ──────────────────────────────────────────────
# 日志配置
# ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            Path(__file__).parent / "auto_confirm.log",
            encoding="utf-8"
        ),
    ],
)
log = logging.getLogger("AutoConfirm")

# ──────────────────────────────────────────────
# 配置
# ──────────────────────────────────────────────
@dataclass
class Config:
    # 扫描间隔（秒）
    poll_interval: float = 1.2

    # 图像匹配置信度（0-1），越高越严格
    image_confidence: float = 0.75

    # OCR 目标按钮文字（不区分大小写）
    target_labels: list = field(default_factory=lambda: [
        "accept", "accept all", "apply", "apply all",
        "confirm", "yes", "ok", "run", "save", "allow",
        "continue", "proceed", "approve",
        # 中文
        "接受", "接受所有", "确认", "应用", "保存", "继续",
    ])

    # 危险词黑名单（包含时不点击）
    skip_labels: list = field(default_factory=lambda: [
        "delete", "remove", "discard", "drop",
        "force", "overwrite", "reset", "cancel",
        "删除", "丢弃", "覆盖", "重置",
    ])

    # 点击后冷却（秒），防止重复点击
    click_cooldown: float = 2.0

    # 截图区域（None = 全屏），可缩小范围提升性能
    # 格式: (left, top, width, height)
    capture_region: Optional[tuple] = None

    # 模板图片目录
    template_dir: Path = Path(__file__).parent / "templates"

    # 是否启用 OCR 引擎
    use_ocr: bool = True

    # 是否启用图像模板引擎
    use_template: bool = True

    # macOS 通知
    use_notification: bool = True


CONFIG = Config()

# ──────────────────────────────────────────────
# 状态
# ──────────────────────────────────────────────
class State:
    running = True
    enabled = True
    last_click_time = 0.0
    click_count = 0

STATE = State()

# ──────────────────────────────────────────────
# macOS 通知
# ──────────────────────────────────────────────
def notify(title: str, msg: str):
    if CONFIG.use_notification:
        os.system(
            f'osascript -e \'display notification "{msg}" with title "{title}"\''
        )

# ──────────────────────────────────────────────
# 截图工具
# ──────────────────────────────────────────────
def grab_screen() -> Image.Image:
    if CONFIG.capture_region:
        l, t, w, h = CONFIG.capture_region
        return ImageGrab.grab(bbox=(l, t, l + w, t + h))
    return ImageGrab.grab()

# ──────────────────────────────────────────────
# 引擎 1：OCR 文字识别
# ──────────────────────────────────────────────
def preprocess_for_ocr(img: Image.Image) -> Image.Image:
    """增强图像，提高 OCR 准确率"""
    img = img.convert("L")                              # 灰度
    img = ImageEnhance.Contrast(img).enhance(2.0)       # 提升对比度
    img = img.filter(ImageFilter.SHARPEN)               # 锐化
    # 放大 2x，tesseract 对小字识别更好
    w, h = img.size
    img = img.resize((w * 2, h * 2), Image.LANCZOS)
    return img

def find_button_by_ocr(screenshot: Image.Image) -> Optional[tuple]:
    """
    用 OCR 扫描屏幕上的按钮文字
    返回 (center_x, center_y) 或 None
    """
    if not OCR_AVAILABLE or not CONFIG.use_ocr:
        return None

    try:
        processed = preprocess_for_ocr(screenshot)
        # 获取每个词的位置信息
        data = pytesseract.image_to_data(
            processed,
            output_type=pytesseract.Output.DICT,
            config="--psm 11",  # 稀疏文字模式，适合 UI
            lang="eng+chi_sim",
        )
    except Exception as e:
        log.debug(f"OCR 失败: {e}")
        return None

    n = len(data["text"])
    sw, sh = screenshot.size
    scale = 2  # 对应 preprocess 里的 resize 倍数

    for i in range(n):
        word = (data["text"][i] or "").strip()
        conf = int(data["conf"][i] or 0)

        if not word or conf < 50:
            continue

        word_lower = word.lower()

        # 黑名单检查
        if any(s in word_lower for s in CONFIG.skip_labels):
            continue

        # 目标词匹配
        if any(t in word_lower for t in CONFIG.target_labels):
            # 坐标换算回原始截图尺寸
            x = data["left"][i] / scale
            y = data["top"][i] / scale
            w = data["width"][i] / scale
            h = data["height"][i] / scale

            cx = int(x + w / 2)
            cy = int(y + h / 2)

            # 如果有截图偏移，加上偏移量
            if CONFIG.capture_region:
                cx += CONFIG.capture_region[0]
                cy += CONFIG.capture_region[1]

            log.info(f"[OCR] 发现按钮: '{word}' (置信度:{conf}%) @ ({cx}, {cy})")
            return (cx, cy, word)

    return None

# ──────────────────────────────────────────────
# 引擎 2：图像模板匹配
# ──────────────────────────────────────────────
def load_templates() -> dict:
    """加载 templates/ 目录下的所有 .png 模板"""
    templates = {}
    if not CONFIG.template_dir.exists():
        CONFIG.template_dir.mkdir(parents=True)
        log.info(f"已创建模板目录: {CONFIG.template_dir}")
        log.info("请将按钮截图（.png）放入该目录，文件名即为按钮名称")
        return templates

    for f in CONFIG.template_dir.glob("*.png"):
        img = cv2.imread(str(f), cv2.IMREAD_COLOR)
        if img is not None:
            templates[f.stem] = img
            log.info(f"加载模板: {f.stem}")

    return templates

TEMPLATES = {}

def find_button_by_template(screenshot: Image.Image) -> Optional[tuple]:
    """
    用模板匹配在截图中找按钮
    返回 (center_x, center_y, name) 或 None
    """
    if not CV2_AVAILABLE or not CONFIG.use_template or not TEMPLATES:
        return None

    # PIL → numpy → BGR
    screen_np = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

    for name, template in TEMPLATES.items():
        # 检查黑名单
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

            log.info(f"[模板] 发现按钮: '{name}' (匹配度:{max_val:.2%}) @ ({cx}, {cy})")
            return (cx, cy, name)

    return None

# ──────────────────────────────────────────────
# 点击执行
# ──────────────────────────────────────────────
def do_click(cx: int, cy: int, label: str):
    now = time.time()
    if now - STATE.last_click_time < CONFIG.click_cooldown:
        log.debug(f"冷却中，跳过点击: {label}")
        return

    STATE.last_click_time = now
    STATE.click_count += 1

    # 移动到目标位置（稍微平滑，不要瞬移）
    pyautogui.moveTo(cx, cy, duration=0.15)
    pyautogui.click(cx, cy)

    log.info(f"✅ 点击成功: [{label}] @ ({cx}, {cy})  累计:{STATE.click_count}次")
    notify("🤖 AutoConfirm", f'已自动点击: "{label}"')

# ──────────────────────────────────────────────
# 主扫描循环
# ──────────────────────────────────────────────
def scan_once():
    """执行一次屏幕扫描"""
    try:
        screenshot = grab_screen()

        # 优先用模板（快），再用 OCR（慢但更通用）
        result = find_button_by_template(screenshot)
        if not result:
            result = find_button_by_ocr(screenshot)

        if result:
            cx, cy, label = result
            do_click(cx, cy, label)

    except Exception as e:
        log.error(f"扫描异常: {e}", exc_info=False)

def run_loop():
    log.info("=" * 50)
    log.info("AutoConfirm 启动")
    log.info(f"  扫描间隔: {CONFIG.poll_interval}s")
    log.info(f"  OCR 引擎: {'✅' if OCR_AVAILABLE and CONFIG.use_ocr else '❌'}")
    log.info(f"  模板引擎: {'✅' if CV2_AVAILABLE and CONFIG.use_template else '❌'}")
    log.info(f"  模板目录: {CONFIG.template_dir}")
    log.info("按 Ctrl+C 停止")
    log.info("=" * 50)

    global TEMPLATES
    if CV2_AVAILABLE:
        TEMPLATES = load_templates()

    while STATE.running:
        if STATE.enabled:
            scan_once()
        time.sleep(CONFIG.poll_interval)

# ──────────────────────────────────────────────
# 命令行控制（另起线程监听输入）
# ──────────────────────────────────────────────
def input_listener():
    """监听键盘输入，支持运行时控制"""
    print("\n命令: [p]暂停/恢复  [s]状态  [q]退出\n")
    while STATE.running:
        try:
            cmd = input().strip().lower()
            if cmd == "p":
                STATE.enabled = not STATE.enabled
                status = "▶️  已恢复" if STATE.enabled else "⏸  已暂停"
                print(f"\n{status}\n")
            elif cmd == "s":
                print(
                    f"\n状态: {'运行中' if STATE.enabled else '已暂停'} | "
                    f"累计点击: {STATE.click_count} 次\n"
                )
            elif cmd == "q":
                STATE.running = False
                print("\n正在退出...")
                break
        except (EOFError, KeyboardInterrupt):
            break

# ──────────────────────────────────────────────
# 优雅退出
# ──────────────────────────────────────────────
def handle_signal(sig, frame):
    log.info(f"\n收到信号 {sig}，正在退出... (共点击 {STATE.click_count} 次)")
    STATE.running = False
    sys.exit(0)

signal.signal(signal.SIGINT, handle_signal)
signal.signal(signal.SIGTERM, handle_signal)

# ──────────────────────────────────────────────
# 入口
# ──────────────────────────────────────────────
if __name__ == "__main__":
    # 允许 pyautogui 故障保护（移到左上角立即停止）
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.05

    # 后台线程监听键盘命令
    t = threading.Thread(target=input_listener, daemon=True)
    t.start()

    run_loop()
