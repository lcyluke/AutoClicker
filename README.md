<p align="center">
  <a href="https://github.com/lcyluke/AutoClicker/blob/main/autoclicker.mp4">
    <img src="AutoClicker.png" alt="▶ Watch Demo" width="400">
  </a>
  <br><b>▶ Click the logo to watch demo</b>
</p>

# AutoClicker

<p align="center">
  <a href="README.md"><b>English</b></a> | <a href="README_CN.md">中文</a>
</p>

> IDE multi-session auto clicker — automatically click Run, Accept, Confirm buttons across VS Code, Cursor, Kiro, Antigravity and other IDEs.

## In One Sentence

Got N IDE windows running tasks, each needing a **Run** / **Accept** / **Continue** click every few minutes? AutoClicker watches your screen, spots the button, and clicks it — so you don't have to.

## Supported IDEs

| IDE | Run Button | Dialog Confirm | Tab Switching |
|-----|-----------|----------------|---------------|
| VS Code | ✅ | ✅ | ✅ |
| Cursor | ✅ | ✅ | ✅ |
| Kiro | ✅ | ✅ | ✅ |
| Antigravity | ✅ | ✅ | ✅ |
| Others (OCR) | ✅ | ✅ | ✅ |

## Two Detection Modes

**Mode 1: OCR Text Detection (Universal)**
Scans your screen for **Run / Accept / Continue / Yes / Confirm** button text. No prior screenshots needed.

```
Works out of the box — just brew install tesseract
```

**Mode 2: Image Template Matching (Precise)**
Screenshot buttons as templates. More accurate for fixed IDE layouts.

## Quick Start

### 1. Install Dependencies

**Python packages (all platforms):**
```bash
pip install -r requirements.txt
```

**Tesseract OCR engine:**

| Platform | Command |
|----------|---------|
| macOS | `brew install tesseract` |
| Windows | Download installer from [GitHub](https://github.com/UB-Mannheim/tesseract/wiki) |
| Linux | `sudo apt install tesseract-ocr` or `sudo dnf install tesseract` |

**Windows optional (desktop notifications):**
```bash
pip install win10toast
```

### 2. System Permissions

| Platform | What to do |
|----------|------------|
| **macOS** | System Settings → Privacy & Security → enable **Accessibility** + **Screen Recording** for Terminal |
| **Windows** | No extra permissions needed |
| **Linux** | No extra permissions needed (X11/Wayland screen access by default) |

### 3. Record Click Sequence

```bash
python clicker.py
# Choose 1 → Record mode
# Hold mouse on tab position for 5s → auto-captured
# Hold mouse on Run button center for 7s → auto-captured
# Repeat for N tabs
```

### 4. Start Auto-Clicking

```bash
python clicker.py
# Choose 3 → Start loop
# Switch to IDE window within 3s, then watch it click
```

Runtime controls:

| Action | How |
|--------|-----|
| Pause / Resume | Press `p` + Enter |
| Check status | Press `s` + Enter |
| Exit | Press `q` + Enter or Ctrl+C |
| Emergency stop | Move mouse to top-left corner |

## Language & Update

```bash
python clicker.py --lang en     # English (--lang=en also works)
python clicker.py --lang zh     # 中文 (--lang=zh also works)
python clicker.py               # defaults to English
python clicker.py --version     # show version
python clicker.py --update      # git pull to latest
```

All three scripts (`clicker.py`, `auto_confirm.py`, `capture_template.py`) support `--lang`, `--version`, and `--update`.

## How It Works

```
┌──────────────────────────────────────┐
│  Loop: Tab1 → Tab2 → Tab3 → Tab1...  │
│                                      │
│  ① Click tab                         │
│  ② OCR scan for Run button (up to 7s)│
│  ③ Found → click Run                 │
│  ④ Wait for task → next tab          │
│  ⑤ Not found → skip, next            │
└──────────────────────────────────────┘
```

## Configuration

Edit `click_sequence.json`:

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

| Param | Description | Default |
|-------|-------------|---------|
| `run_scan_timeout` | Max OCR scan time per tab (s) | 7 |
| `run_scan_interval` | Interval between scans (s) | 0.8 |
| `after_run_delay` | Wait after clicking Run (s) | 3 |
| `after_tab_delay` | Wait after clicking tab (s) | 1.0 |
| `scan_width` | Scan area width (px) | 100 |
| `scan_height` | Scan area height (px) | 36 |
| `loop_delay` | Extra wait between rounds (s) | 2 |

## Files

```
auto_confirm/
├── clicker.py              # Main: record + loop + OCR click
├── auto_confirm.py         # Auto-confirm: template + OCR scan
├── capture_template.py     # Template screenshot tool
├── requirements.txt        # Python deps
├── templates/              # Button template images
├── click_sequence.json     # Recorded click sequence config
├── README.md               # English docs
└── README_CN.md            # 中文文档
```

## License

MIT — see [LICENSE](LICENSE)

## Safety

- Mouse to top-left corner = emergency stop (PyAutoGUI FAILSAFE)
- Ctrl+C = graceful exit
- All clicks logged in `auto_confirm.log`

## Requirements

- **macOS** / **Windows** / **Linux**
- Python 3.9+
- Tesseract OCR
- macOS: Screen Recording + Accessibility permissions
