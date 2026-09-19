# File Organizer

[中文](./README.md) | English

A Windows desktop file archiving tool: drop files onto window panes and they are automatically archived into the target directory according to rules (year/month, ctime/mtime time modes, copy/move). Also includes Everything search integration, pane color and rename options, window state memory, high-DPI support, and more.

- Tech stack: Python + tkinter + tkinterdnd2 (drag-and-drop), with ctypes calling the Win32 API directly (title-bar active state, DragAcceptFiles, file creation-time read/write)
- Packaging: PyInstaller single-file exe (`文件归档器.spec`, with embedded icon.ico, UPX-compressed)
- Runtime log: `drop.log` (startup / drag-and-drop initialization records)

## Move with time structure

The「☑ 带时间结构移动」(Move with time structure) toggle in the bottom control bar is the master switch for how files are transported. It is off by default.

**The problem it solves**: the default path uses `shutil.move`. Same drive is fine, but **across drives it genuinely copies** — and copying resets a file's "creation time" to the current moment. `shutil.copy2` only preserves the modification time, not the creation time. So after moving a batch of old photos you would find their creation dates all turned into today.

**What it does**:

| Case | Method | Result |
|---|---|---|
| Same drive | `os.rename` | Instant, regardless of file count; all timestamps preserved |
| Across drives | Copy, then write the creation time back | Neither creation nor modification time changes |
| Dragging a folder | The whole tree moves as one unit | Every file and subfolder keeps its creation time |

The same-drive case is worth emphasising: a folder with 3000 files moves in **a few milliseconds**, because only the directory entry is renamed — not a single byte of content is touched.

**Checking it hides the「修改时间 / 创建时间」buttons.** Those two buttons select *which timestamp to sort by*; once "Move with time structure" is on, structure is no longer split by time, so leaving them visible would only mislead. Unchecking restores them.

Relationship with 「仅复制」(copy only): with both on, the copy also keeps its creation time (it is a copy, not a move, so the source stays).

**Implementation notes**: `os.utime` can only change modification/access times, never creation time — that requires the Win32 `CreateFileW` + `SetFileTime`. Opening a directory handle requires `FILE_FLAG_BACKUP_SEMANTICS`. A directory's creation time must be written last, after all its contents have settled (writing into a directory refreshes its own timestamps), so `os.walk(topdown=False)` processes depth-first.

Tests live in `test_keep_time.py` (21 assertions, including a reverse control proving `copy2` cannot preserve creation time).

## Building

```bash
pyinstaller 文件归档器.spec
```

The output is `dist/文件归档器.exe` (`build/`, `dist/`, and `__pycache__/` are not committed to the repo; they are reproducible).

## A note on this repository's history

This project was developed in Claude Code, but its session edit records could not be recovered (all local AI session logs were searched; no Edit/Write events point to this project). Therefore this repository was created **as an archive of the current state**, and the commit-by-commit history cannot be reconstructed. The development timeline inferred from file timestamps:

| Time (2026) | Event |
|---|---|
| 06-29 | icon.ico icon created |
| 07-04 23:37 | last run record in drop.log (drag-and-drop initialized normally) |
| 07-05 00:27–00:29 | 文件归档器.py last modified → .spec updated → packaged as dist/文件归档器.exe |

In short: development spanned from late June 2026 to the early hours of 07-05, closing out with one complete packaging run.
