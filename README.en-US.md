<div align="center">

# File Organizer

**Drag once, and every file lands where it belongs — by date, by year, by your habit**

[中文](./README.md) | English

![Platform](https://img.shields.io/badge/platform-Windows-0078D6?style=flat-square&logo=windows&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.x-3776AB?style=flat-square&logo=python&logoColor=white)

</div>

---

## ✨ Why this tool

| | File Organizer | Manual sorting |
|---|---|---|
| 🖱 Archiving | Drop files onto a zone, release, done | Open folder → copy → paste → rename |
| ⏱ Time rules | Created / modified time switchable, year / month layers, down to the day | Check dates and build folders by hand |
| 📅 That Day in History | **Browse old files back through the years**, flip years with one click | No such concept |
| 🔎 Locating | **Everything integration** — jump straight to the archived spot | Find and open it yourself |
| 🧊 UI | Title bar never grays out, per-monitor high-DPI aware, moves run on a background thread | —— |

**Nine zones are just the nine folders you always visit: screenshots here, bills there, photos over there — just drag.**

---

## 📑 Features

| | |
|---|---|
| 🖼 **Nine drag zones** | Nine target zones, each bound to any folder; drop to archive under the current rules, with toast feedback |
| ⏱ **Time rules** | Created (ctime) / modified (mtime) one-click switch · automatic year / month layers · "down to day" toggle · copy-only mode (originals untouched) |
| 📅 **That Day in History** | A unique look-back mode: browse old files by year (starts 8 years back), one-click "that day / that month" folders, flip through years freely |
| 🔎 **Everything integration** | Auto-detects Everything.exe; when enabled, opens / locates results with Everything — whole-disk speed |
| 🎨 **Zone personalization** | Per-zone color (color picker) with automatic dark text · rename zones · re-pick paths |
| 🪟 **Window experience** | Position & size remembered · always-on-top toggle · **title bar never grays out** (`WM_NCACTIVATE` intercepted, the window stays "alive" during drops) · per-monitor DPI awareness |
| ⚙️ **Engineering** | Moves / copies run on a background thread — zero UI freeze · config under `%APPDATA%` · PyInstaller single-file exe (UPX packed), download and run |

---

## 🥣 Usage

### Direct download

Grab `文件归档器.exe` (~11 MB, single file) from [Releases](../../releases) and run; config lives in `%APPDATA%\文件归档器\`.

### Run from source

```bash
pip install tkinterdnd2
python 文件归档器.py
```

### Build

```bash
pyinstaller 文件归档器.spec
```

Output: `dist/文件归档器.exe`.

---

## 🧠 Two details worth mentioning

- **Title bar never grays out**: during long drops Windows marks the window "Not Responding" and grays its title bar. This tool subclasses the window procedure via `SetWindowLongPtr` and intercepts `WM_NCACTIVATE`, so the title bar always draws as active — no matter how much you drag.
- **That Day in History**: anchored to each file's created / modified time, old files from different years go back to their own "that day / that month" folders. When revisiting photos, bills or chat backups from years ago, the timeline rewinds in one click.

---

## 📜 Notes

- `dist/文件归档器.exe` and `build/` are committed on purpose as an anti-loss copy (since 2026-09-02); they are regenerable and safe to ignore
- Runtime log: `drop.log` (startup / drop-init records)
