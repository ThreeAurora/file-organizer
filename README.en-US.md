<div align="center">

# File Organizer

**Drag once, and every file lands where it belongs — by date, by year, by your habit**

[中文](./README.md) | English

![Platform](https://img.shields.io/badge/platform-Windows-0078D6?style=flat-square&logo=windows&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.x-3776AB?style=flat-square&logo=python&logoColor=white)

</div>

---

## 📖 What it is

A small Windows desktop tool: nine zones are the nine folders you visit most. Drop files onto a zone and they are archived by time into `year\month\` or `year\month\day\` — screenshots here, bills there, photos over there, no more opening folders and pasting one by one.

- Single-file exe, download and run, no install
- Config lives in `%APPDATA%\文件归档器\`; the in-app「ℹ 使用手册」has a quick guide (Chinese)

## ✨ Features

| | |
|---|---|
| 🖼 **Nine drag zones** | Each zone is bound to a target folder; drop to archive, with a result toast; click a zone to open its folder |
| ⏱ **Time rules** | Sort by modified / created time, auto-layered by `year / month`, optionally down to the day |
| 📅 **That Day in History** | Look back through old files by year; drop onto a year to archive into "that day" of that year |
| 🗂 **Carry the structure** | Keeps the `year\month\date` structure already present in the source path (instant on the same drive, creation time preserved across drives) |
| 📋 **Copy only** | Copy instead of move; originals stay untouched |
| 🔎 **Everything integration** | With it on, clicking a zone searches that folder in Everything |
| 🎨 **Zone personalization** | Right-click a zone: rename / re-pick path / set color |
| 🪟 **Window experience** | Always-on-top, position & size remembered, high-DPI aware; stays responsive and never grays out during large moves |
| ⚙ **Settings** | Bottom-bar「⚙ 设置」: whether "carry the structure" defaults on at launch, and whether mismatches fall back to time sorting |

## 🚀 Usage

### Download

Get the latest exe from [Releases](../../releases); double-click to run, no install.

### First run

Zones start as「请选择路径」(choose a path) — click each zone and pick its target folder. To rename a zone, re-pick its path or change its color, right-click the zone.

### Everyday archiving

- Drop files / folders onto a zone → archived by the current rules into `target folder \ year \ month \`, with a result toast
- Click a zone → open its folder
- Drop onto the「通用整理」(general staging) area → also archived, but right next to the files themselves
- Name collisions become `_1`, `_2`, … — existing files are never overwritten; up to 200 items per drop

### Bottom-bar toggles

| Toggle | Effect |
|---|---|
| 修改时间 / 创建时间 | Which timestamp decides the archive layers |
| 具体到日 | On: `2026\07\2026-07-01`; off: `2026\07` only |
| 仅复制 | Copy instead of move |
| 附带结构 | Carry the source structure (see below) |
| 那年今日 | Year look-back mode (see below) |
| 置顶窗口 | Keep the window on top |
| Everything | Clicking a zone searches that path in Everything; use「自动查找」/「选择路径」to point at Everything.exe |

### That Day in History

Check「☑ 那年今日」, then click any zone to enter the year grid (the last 9 years):

- Drop files onto a year → archived into "that day" of that year. E.g. on July 1, dropping onto「2018」→ `target folder\2018\07\2018-07-01`
- Click a year → open that year's "today" folder
- 「新建今天」/「新建本月」→ create "that day" / every date folder of the current month under the selected year (existing ones are skipped)
- 「◀ 往前 9 年」flips to earlier years;「返回」exits the mode

### Carry the structure

Instead of each item's own timestamp, the structure already present in the source path decides the destination:

```
drop   G:\videos\2016\03\20160301\a.mp4
lands  target folder\2016\03\2016-03-01\a.mp4
```

- Date folders in both `20160301` and `2016-03-01` styles are recognized; stored with dashes
- Same drive: instant (only ownership changes); across drives: copied and the creation time is written back, so it is not reset to today; folders move as a whole tree with every timestamp preserved
- Non-matching items are sorted by time by default; turn that option off in「⚙ 设置」to reject the whole batch instead
- The「通用整理」area has no fixed root and always sorts by time

### Run from source

```bash
pip install tkinterdnd2
python 文件归档器.py
```

Build: `pyinstaller 文件归档器.spec` → output in `dist/`.
