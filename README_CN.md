<p align="center">
  <a href="https://github.com/lcyluke/AutoClicker/blob/main/autoclicker.mp4">
    <img src="AutoClicker.png" alt="▶ 观看演示" width="400">
  </a>
  <br><b>▶ 点击 Logo 观看演示视频</b>
</p>

# AutoClicker

<p align="center">
  <a href="README.md">English</a> | <a href="README_CN.md"><b>中文</b></a>
</p>

> IDE 多 session 自动点击器 — 替你在 VS Code、Cursor、Kiro、Antigravity 等 IDE 里自动点按钮、切标签、确认弹窗。

## 一句话

同时开着 N 个 IDE 窗口跑任务，每个都需要隔几分钟点一下 **Run** / **Accept** / **Continue**？AutoClicker 帮你盯着，看到按钮就点，省下反复切窗口的重复劳动。

## 支持的 IDE

| IDE | Run 按钮 | 弹窗确认 | 标签切换 |
|-----|----------|----------|---------|
| VS Code | ✅ | ✅ | ✅ |
| Cursor | ✅ | ✅ | ✅ |
| Kiro | ✅ | ✅ | ✅ |
| Antigravity | ✅ | ✅ | ✅ |
| 其他（OCR通用） | ✅ | ✅ | ✅ |

## 两种识别模式

**模式 1：OCR 文字识别（通用）**
自动识别屏幕上的 **Run / Accept / Continue / Yes / Confirm / 确认 / 接受** 等按钮文字，无需事先截图。

```
开箱即用，brew install tesseract 就行
```

**模式 2：图像模板匹配（精准）**
截取按钮图片当模板，识别更精准，适合固定 IDE 环境。

## 快速开始

### 1. 安装依赖

**Python 包（全平台通用）：**
```bash
pip install -r requirements.txt
```

**Tesseract OCR 引擎：**

| 平台 | 命令 |
|------|------|
| macOS | `brew install tesseract` |
| Windows | 从 [GitHub](https://github.com/UB-Mannheim/tesseract/wiki) 下载安装包 |
| Linux | `sudo apt install tesseract-ocr` 或 `sudo dnf install tesseract` |

**Windows 可选（桌面通知）：**
```bash
pip install win10toast
```

### 2. 系统权限

| 平台 | 操作 |
|------|------|
| **macOS** | 系统设置 → 隐私与安全性 → 开启 **辅助功能** + **屏幕录制** 给 Terminal |
| **Windows** | 无需额外授权 |
| **Linux** | 无需额外授权（X11/Wayland 默认允许截屏） |

### 3. 录制点击序列

```bash
python clicker.py
# 选 1 → 录制模式
# 把鼠标放到标签位置等 5 秒 → 自动记录坐标
# 把鼠标放到 Run 按钮正中心等 7 秒 → 自动记录坐标
# 重复 N 个标签页
```

### 4. 开始自动点击

```bash
python clicker.py
# 选 3 → 循环运行
# 3 秒内切换到 IDE 窗口，然后就看着它自己点
```

运行时控制：

| 操作 | 方式 |
|------|------|
| 暂停/恢复 | 按 `p` + Enter |
| 查看状态 | 按 `s` + Enter |
| 退出 | 按 `q` + Enter 或 Ctrl+C |
| 紧急停止 | 鼠标移到屏幕左上角 |

## 语言切换 & 更新

```bash
python clicker.py --lang en     # English (--lang=zh 也支持)
python clicker.py --lang zh     # 中文 (--lang zh 也支持)
python clicker.py               # 默认英文
python clicker.py --version     # 查看版本
python clicker.py --update      # git pull 更新到最新
```

三个脚本（`clicker.py`、`auto_confirm.py`、`capture_template.py`）均支持 `--lang`、`--version`、`--update`。

## 工作原理

```
┌──────────────────────────────────────┐
│  循环: Tab1 → Tab2 → Tab3 → Tab1...  │
│                                      │
│  ① 点击标签页                        │
│  ② OCR 扫描 Run 按钮（最多等7秒）     │
│  ③ 找到 → 点击 Run                   │
│  ④ 等任务跑完 → 切下一个标签          │
│  ⑤ 找不到 → 跳过，下一个             │
└──────────────────────────────────────┘
```

## 配置

编辑 `click_sequence.json`：

```json
{
  "run_scan_timeout": 7,
  "run_scan_interval": 0.8,
  "after_run_delay": 3,
  "after_tab_delay": 1.0,
  "scan_width": 100,
  "scan_height": 36,
  "loop_delay": 2
}
```

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `run_scan_timeout` | OCR 扫描超时（秒） | 7 |
| `run_scan_interval` | 扫描间隔（秒） | 0.8 |
| `after_run_delay` | 点 Run 后等多久（秒） | 3 |
| `after_tab_delay` | 点标签后等多久（秒） | 1.0 |
| `scan_width` | 扫描区域宽度（像素） | 100 |
| `scan_height` | 扫描区域高度（像素） | 36 |
| `loop_delay` | 每轮结束额外等待（秒） | 2 |

## 文件说明

```
auto_confirm/
├── clicker.py              # 主程序：录制 + 循环点击 + OCR
├── auto_confirm.py         # 自动确认：模板匹配 + OCR 通用扫描
├── capture_template.py     # 按钮模板截图工具
├── requirements.txt        # Python 依赖
├── templates/              # 按钮模板图片
├── click_sequence.json     # 录制的点击序列配置
├── README.md               # English docs
└── README_CN.md            # 中文文档
```

## 许可

MIT — 详见 [LICENSE](LICENSE)

## 安全

- 鼠标移到屏幕左上角 = 紧急停止（PyAutoGUI FAILSAFE）
- Ctrl+C = 优雅退出
- 所有点击操作记录在 `auto_confirm.log`

## 系统要求

- **macOS** / **Windows** / **Linux**
- Python 3.9+
- Tesseract OCR
- macOS：需要屏幕录制 + 辅助功能权限
