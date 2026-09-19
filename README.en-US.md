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
| 🗂 **Carry the structure** | Moves things whole, never taken apart: **instant rename on the same drive, and copying across drives does not rewrite creation time**. Checking it tucks away the two time buttons |
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

## 🗂 Carry the structure

The「☑ 附带结构」(Carry the structure) toggle in the bottom bar is the master switch for how things are transported. Off by default.

**The problem it solves**: the default path uses `shutil.move`. Same drive is fine, but **across drives it genuinely copies** — and copying resets a file's *creation time* to the current moment. `shutil.copy2` only preserves the modification time, not the creation time. So after moving a batch of old photos you would find their creation dates **all turned into today**.

**What it does**:

| Case | Method | Result |
|---|---|---|
| Same drive | `os.rename` — only the directory entry is renamed | **Instant**, regardless of file count; every timestamp preserved |
| Across drives | Copy, then write the creation time back | Neither creation nor modification time changes |
| Dragging a folder | The whole tree moves as one unit | Every file and subfolder keeps its creation time |

The same-drive case is worth emphasising: a folder with 3000 files moves in **a few milliseconds**, because not a single byte of content is touched — only ownership of the name changes.

**Checking it tucks away the「修改时间 / 创建时间」buttons** — those two select *which timestamp to sort by*; once this is on, structure is no longer split by time, so leaving them visible would only mislead. Unchecking restores them.

Combined with 「仅复制」(copy only): the resulting copy keeps its creation time too (it is a copy, not a move, so the source stays).

---

## 🧠 Three details worth mentioning

- **Title bar never grays out**: during long drops Windows marks the window "Not Responding" and grays its title bar. This tool subclasses the window procedure via `SetWindowLongPtr` and intercepts `WM_NCACTIVATE`, so the title bar always draws as active — no matter how much you drag.
- **That Day in History**: anchored to each file's created / modified time, old files from different years go back to their own "that day / that month" folders. When revisiting photos, bills or chat backups from years ago, the timeline rewinds in one click.
- **Creation-time fidelity**: `os.utime` can only change modification / access times, never creation time — that needs the Win32 `CreateFileW` + `SetFileTime`, and opening a *directory* handle requires `FILE_FLAG_BACKUP_SEMANTICS`. A directory's creation time must be written **after all its contents have settled** (writing into a directory refreshes its own timestamps), hence `os.walk(topdown=False)` to go depth-first.

Tests live in `test_keep_time.py`: 21 assertions, including a reverse control proving `copy2` cannot preserve creation time.

### A third, actually

- **Creation-time fidelity**: `os.utime` can only change modification / access times, never creation time — that needs the Win32 `CreateFileW` + `SetFileTime`, and opening a *directory* handle requires `FILE_FLAG_BACKUP_SEMANTICS`. A directory's creation time must be written **after all its contents have settled** (writing into a directory refreshes its own timestamps), hence `os.walk(topdown=False)` to go depth-first.

Tests live in `test_keep_time.py`: 21 assertions, including a reverse control proving `copy2` cannot preserve creation time.

---

## 📜 Notes

- `dist/文件归档器.exe` and `build/` are committed on purpose as an anti-loss copy (since 2026-09-02); they are regenerable and safe to ignore
- Runtime log: `drop.log` (startup / drop-init records)
