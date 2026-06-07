#!/usr/bin/env python3
"""
模板截图工具 - 截取按钮图像保存为模板
用法：python capture_template.py

操作方式：
  运行后会倒计时 3 秒，期间请把鼠标移到目标按钮上
  脚本会自动截取鼠标周围 120x40 像素区域作为模板
"""

import time
import sys
from pathlib import Path

import pyautogui
from PIL import Image

TEMPLATE_DIR = Path(__file__).parent / "templates"
TEMPLATE_DIR.mkdir(exist_ok=True)

# 截取区域大小（宽 x 高）
CAPTURE_W = 140
CAPTURE_H = 44


def capture_around_mouse(name: str):
    print(f"\n3 秒后截取鼠标位置的按钮区域，请将鼠标移到目标按钮上...")
    for i in range(3, 0, -1):
        print(f"  {i}...", end="\r")
        time.sleep(1)

    mx, my = pyautogui.position()
    left   = mx - CAPTURE_W // 2
    top    = my - CAPTURE_H // 2
    right  = left + CAPTURE_W
    bottom = top + CAPTURE_H

    # macOS Retina 屏幕 grab 会是 2x，这里直接用 pyautogui.screenshot
    img = pyautogui.screenshot(region=(left, top, CAPTURE_W, CAPTURE_H))

    save_path = TEMPLATE_DIR / f"{name}.png"
    img.save(save_path)
    print(f"\n✅ 已保存模板: {save_path}")
    print(f"   尺寸: {img.size}  坐标: ({left},{top})-({right},{bottom})")

    # 预览
    img.show()


if __name__ == "__main__":
    print("=" * 40)
    print("按钮模板截图工具")
    print("=" * 40)

    name = input("输入模板名称（如 accept / apply / 确认）: ").strip()
    if not name:
        print("名称不能为空")
        sys.exit(1)

    capture_around_mouse(name)

    again = input("\n继续截取另一个模板？(y/n): ").strip().lower()
    while again == "y":
        name = input("输入模板名称: ").strip()
        if name:
            capture_around_mouse(name)
        again = input("\n继续？(y/n): ").strip().lower()

    print("\n完成！模板已保存到:", TEMPLATE_DIR)
    print("重启 auto_confirm.py 即可加载新模板")
