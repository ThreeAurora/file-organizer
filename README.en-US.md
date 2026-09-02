# File Organizer

[中文](./README.md) | English

A Windows desktop file archiving tool: drop files onto window panes and they are automatically archived into the target directory according to rules (year/month, ctime/mtime time modes, copy/move). Also includes Everything search integration, pane color and rename options, window state memory, high-DPI support, and more.

- Tech stack: Python + tkinter + tkinterdnd2 (drag-and-drop), with ctypes calling the Win32 API directly (title-bar active state, DragAcceptFiles)
- Packaging: PyInstaller single-file exe (`文件归档器.spec`, with embedded icon.ico, UPX-compressed)
- Runtime log: `drop.log` (startup / drag-and-drop initialization records)

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
