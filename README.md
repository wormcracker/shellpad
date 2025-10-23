# Shellpad

> **A lightweight terminal-based notes editor**  
> Minimal, fast, and markdown-friendly — perfect for note-takers who live in the terminal.

---

## 🚀 Overview

**Shellpad** is a simple curses-powered Markdown notebook for your terminal.  
It stores all notes in a single `shellpad.md` file and lets you view, edit, and manage them directly in the console — no extra dependencies, no bloat.

---

## ✨ Features

- 🗒️ Markdown-style notes stored in one file
- ✅ Checkbox preview for `[ ]` and `[x]` tasks
- ⚡ Realtime autosave
- 🖊️ In-terminal or external editor (e.g., Vim, Nano)
- 📋 System clipboard integration
- 🔗 Open URLs directly from the editor
- 🧭 Simple, keyboard-only navigation

---

## 🧩 Installation

- For Mac and Linux

```bash
pipx install shellpad
```

- For Windows

```bash
pipx install shellpad[windows]
```

## 🧩 Running locally

1. Clone the repository:

```bash
git clone https://github.com/wormcracker/shellpad.git
cd shellpad
```

2. Run directly:

```bash
python3 shellpad.py
```

3. (Optional) Make executable:

```bash
chmod +x shellpad.py
./shellpad.py
```

**Dependencies:**  
Only Python 3.8+ — no external modules required.  
(Optional clipboard tools: `xclip`, `xsel`, or `wl-clipboard` on Linux.)

---

## 🪶 Usage

### Basic Controls

| Mode          | Key            | Action                             |
| ------------- | -------------- | ---------------------------------- |
| **List view** | `j / k`        | Move down / up                     |
|               | `a`            | Add new note                       |
|               | `o` or `Enter` | Open note in internal editor       |
|               | `O`            | Open in external editor            |
|               | `y`            | Copy note internally               |
|               | `p`            | Paste copied note / clipboard      |
|               | `Y`            | Copy note body to system clipboard |
|               | `r`            | Rename note                        |
|               | `d`            | Delete note                        |
|               | `[` / `]`      | Move note up / down                |
|               | `?`            | Show help                          |
|               | `q`            | Quit                               |
| **Editor**    | `ESC`          | Save and return                    |
|               | `Ctrl+V`       | Paste from system clipboard        |
|               | `Ctrl+W`       | Delete previous word               |

---

## ⚙️ Configuration

Config file:  
`~/.config/shellpad/config.cfg`
`%APPDATA%\shellpad\config.cfg (Windows)`

Example:

```
notebook_file: ~/shellpad.md
external_editor: false
default_editor: vim
wrap_lines: true
realtime_save: true
doing_symbol: +
done_symbol: -
```

**Options:**

- `notebook_file` — Path to your notes file
- `external_editor` — Use system editor (true/false)
- `default_editor` — Which external editor to use
- `realtime_save` — Save as you type
- `doing_symbol`, `done_symbol` — Customize preview icons

---

## 🗂️ Notes Format

Notes are stored in Markdown under H1 titles:

```markdown
# Grocery List

[ ] Buy milk
[x] Bread bought

# Ideas

A concept for a terminal-based wiki.
```

---

## 💡 Tips

- Copy and paste notes internally with `y` and `p`.
- Press `?` anytime for the built-in help window.
- Preview automatically wraps long lines.
- Works on Linux, macOS, and Windows (PowerShell-based clipboard).

---

## ⚖️ License

**MIT License** — © 2025 [sushant](https://github.com/wormcracker)

Use, modify, and share freely.

---

## 🌐 Links

- **GitHub:** [wormcracker/shellpad](https://github.com/wormcracker/shellpad)
- **Author:** sushant
- **Language:** Python 3 (no dependencies)

---

> “Simplicity is the final sophistication — Shellpad keeps your notes close and your focus closer.”
