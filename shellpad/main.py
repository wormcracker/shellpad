#!/usr/bin/env python3
"""
Shellpad — lightweight terminal notes editor
Author: sushant
GitHub: github.com/wormcracker
"""
import curses
import textwrap
import subprocess
import tempfile
import os
import re
from pathlib import Path
from dataclasses import dataclass, field, replace
from typing import List, Optional, Dict

DEFAULT_CONFIG = {
    'notebook_file': str(Path.home() / 'shellpad.md'),
    'external_editor': 'false',
    'default_editor': 'vim',
    'wrap_lines': 'true',
    'startup_note': '',
    'realtime_save': 'true',
    'doing_symbol': '+',
    'done_symbol': '-',
}

if os.name == "nt":
    config_base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
else:
    config_base = Path.home() / ".config"

CONFIG_DIR = config_base / "shellpad"
CONFIG_PATH = CONFIG_DIR / "config.cfg"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

URL_RE = re.compile(r'https?://[^\s]+')
TODO_RE = re.compile(r'^\s*(\[\s?\]|(\[[xX]\]))\s*(.*)$')

@dataclass
class Note:
    title: str
    body: str

@dataclass
class Notebook:
    path: Path
    notes: List[Note] = field(default_factory=list)
    H1 = re.compile(r'^#\s+(.*)$')

    def load(self):
        if not self.path.exists():
            self.notes = [Note("Welcome to Shellpad", "This is your first note.\n\n[ ] Try a todo\n[x] Done task")]
            self.save()
            return
        text = self.path.read_text(encoding='utf-8')
        self.notes.clear()
        cur_t, cur_lines = None, []
        for ln in text.splitlines():
            m = self.H1.match(ln)
            if m:
                if cur_t is not None:
                    self.notes.append(Note(cur_t, '\n'.join(cur_lines).rstrip()))
                cur_t, cur_lines = m.group(1).strip(), []
            elif cur_t is not None:
                cur_lines.append(ln)
        if cur_t is not None:
            self.notes.append(Note(cur_t, '\n'.join(cur_lines).rstrip()))

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        out = []
        for n in self.notes:
            out.append(f"# {n.title}")
            if n.body:
                out.append(n.body.rstrip())
            out.append('')
        self.path.write_text('\n'.join(out).rstrip() + '\n', encoding='utf-8')

def copy_to_system_clipboard(text: str) -> bool:
    try:
        if os.name == 'posix':
            for cmd in (('wl-copy',), ('xclip', '-selection', 'clipboard'), ('xsel', '--clipboard', '--input'), ('pbcopy',)):
                try:
                    subprocess.run(cmd, input=text.encode('utf-8'), check=True, timeout=1)
                    return True
                except Exception:
                    continue
            return False
        else:
            subprocess.run(['clip'], input=text.encode('utf-8'), check=True, timeout=1)
            return True
    except Exception:
        return False

def paste_from_system_clipboard() -> str:
    try:
        if os.name == 'posix':
            for cmd in (('wl-paste','--no-newline'), ('xclip','-selection','clipboard','-o'), ('xsel','--clipboard','--output'), ('pbpaste',)):
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=1)
                    if result.returncode == 0:
                        return result.stdout
                except Exception:
                    continue
            return ""
        else:
            result = subprocess.run(['powershell', '-command', 'Get-Clipboard'], capture_output=True, text=True, timeout=1)
            return result.stdout
    except Exception:
        return ""

def draw_box(win, y, x, h, w, title: str = ""):
    if w < 2 or h < 2:
        return
    try:
        win.addch(y, x, '╭'); win.addch(y, x + w - 1, '╮')
        win.addch(y + h - 1, x, '╰'); win.addch(y + h - 1, x + w - 1, '╯')
        for i in range(1, w - 1):
            win.addch(y, x + i, '─'); win.addch(y + h - 1, x + i, '─')
        for i in range(1, h - 1):
            win.addch(y + i, x, '│'); win.addch(y + i, x + w - 1, '│')
        if title:
            title_text = f" {title} "
            title_x = x + max(0, (w - len(title_text)) // 2)
            win.addstr(y, title_x, title_text)
    except curses.error:
        pass

def simple_prompt(stdscr, prompt: str) -> Optional[str]:
    h, w = stdscr.getmaxyx()
    try:
        stdscr.addstr(h - 1, 0, ' ' * (w - 1))
        stdscr.addstr(h - 1, 1, prompt)
    except curses.error:
        pass
    curses.echo(); curses.curs_set(2)
    s = ""
    base = len(prompt) + 1
    while True:
        try:
            stdscr.move(h - 1, base + len(s)); stdscr.refresh()
        except curses.error:
            pass
        k = stdscr.getch()
        if k in (10, 13):
            curses.noecho(); curses.curs_set(0); return s
        if k == 27:
            curses.noecho(); curses.curs_set(0); return None
        if k in (127, 8, curses.KEY_BACKSPACE):
            if s: s = s[:-1]
            try:
                stdscr.addstr(h - 1, base, ' ' * (w - base - 1)); stdscr.addstr(h - 1, base, s)
            except curses.error:
                pass
        elif 32 <= k <= 126:
            s += chr(k)
            try: stdscr.addch(h - 1, base + len(s) - 1, chr(k))
            except curses.error: pass

def show_help(stdscr):
    h, w = stdscr.getmaxyx()
    bh, bw = min(h - 4, 24), min(w - 8, 80)
    by, bx = (h - bh) // 2, (w - bw) // 2
    win = curses.newwin(bh, bw, by, bx)
    win.clear(); draw_box(win, 0, 0, bh, bw, "Help")
    lines = [
        "List view",
        "  j/k or ↓/↑  navigate",
        "  a           add note",
        "  o / Enter   open editor",
        "  O           open in external editor",
        "  y           copy note (internal)",
        "  p           paste copied note as new (or paste clipboard into note)",
        "  Y           copy note body to system clipboard",
        "  r           rename",
        "  d           delete",
        "",
        "Editor",
        "  ESC         save and return",
        "  Ctrl+W      delete previous word",
    ]
    for i, l in enumerate(lines[:bh - 3]):
        try: win.addstr(1 + i, 2, l)
        except curses.error: pass
    try: win.addstr(bh - 2, 2, "Press any key to close...")
    except curses.error: pass
    win.refresh(); win.getch()

class Editor:
    def __init__(self, stdscr, note: Note, autosave_cb, colors: Dict[str,int], realtime: bool = True):
        self.stdscr = stdscr
        self.note = note
        self.autosave_cb = autosave_cb
        self.colors = colors
        self.realtime = realtime
        self.lines = note.body.split('\n') if note.body != '' else ['']
        self.cy = len(self.lines) - 1
        self.cx = len(self.lines[self.cy]) if self.lines else 0
        self.view_top = 0
        self.view_left = 0
        self.undo = []
        self.redo = []
        self._push_undo()

    def _push_undo(self):
        self.undo.append((list(self.lines), self.cy, self.cx))
        if len(self.undo) > 300:
            self.undo.pop(0)
        self.redo.clear()

    def _maybe_realtime_save(self):
        if self.realtime:
            content = '\n'.join(self.lines)
            try:
                self.autosave_cb(content)
            except Exception:
                pass

    def _do_undo(self):
        if len(self.undo) > 1:
            state = self.undo.pop()
            self.redo.append(state)
            lines, y, x = self.undo[-1]
            self.lines = list(lines)
            self.cy, self.cx = y, x
            self._clamp_cursor()
            self._maybe_realtime_save()

    def _do_redo(self):
        if self.redo:
            state = self.redo.pop()
            self.undo.append(state)
            lines, y, x = state
            self.lines = list(lines)
            self.cy, self.cx = y, x
            self._clamp_cursor()
            self._maybe_realtime_save()

    def _clamp_cursor(self):
        if not self.lines:
            self.lines = ['']
        self.cy = max(0, min(self.cy, len(self.lines) - 1))
        self.cx = max(0, min(self.cx, len(self.lines[self.cy])))

    def insert_text(self, s: str):
        cur = self.lines[self.cy]
        before, after = cur[:self.cx], cur[self.cx:]
        parts = s.splitlines()
        if len(parts) == 1:
            self.lines[self.cy] = before + parts[0] + after
            self.cx += len(parts[0])
        else:
            self.lines[self.cy] = before + parts[0]
            for i, p in enumerate(parts[1:], start=1):
                self.lines.insert(self.cy + i, p)
            self.lines[self.cy + len(parts) - 1] += after
            self.cy += len(parts) - 1
            self.cx = len(parts[-1])
        self._push_undo()
        self._maybe_realtime_save()

    def newline(self):
        cur = self.lines[self.cy]
        before, after = cur[:self.cx], cur[self.cx:]
        self.lines[self.cy] = before
        self.lines.insert(self.cy + 1, after)
        self.cy += 1
        self.cx = 0
        self._push_undo()
        self._maybe_realtime_save()

    def backspace(self):
        if self.cx > 0:
            cur = self.lines[self.cy]
            self.lines[self.cy] = cur[:self.cx - 1] + cur[self.cx:]
            self.cx -= 1
            self._push_undo()
            self._maybe_realtime_save()
        elif self.cy > 0:
            prev = self.lines[self.cy - 1]
            cur = self.lines[self.cy]
            self.cx = len(prev)
            self.lines[self.cy - 1] = prev + cur
            self.lines.pop(self.cy)
            self.cy -= 1
            self._push_undo()
            self._maybe_realtime_save()

    def delete_prev_word(self):
        if self.cx == 0:
            if self.cy == 0:
                return
            prev_len = len(self.lines[self.cy - 1])
            self.lines[self.cy - 1] += self.lines[self.cy]
            self.lines.pop(self.cy)
            self.cy -= 1
            self.cx = prev_len
            self._push_undo()
            self._maybe_realtime_save()
            return
        line = self.lines[self.cy]
        pos = self.cx - 1
        while pos >= 0 and line[pos] == ' ':
            pos -= 1
        while pos >= 0 and line[pos] != ' ':
            pos -= 1
        new_x = pos + 1
        self.lines[self.cy] = line[:new_x] + line[self.cx:]
        self.cx = new_x
        self._push_undo()
        self._maybe_realtime_save()

    def find_url_under_cursor(self) -> Optional[str]:
        if not (0 <= self.cy < len(self.lines)):
            return None
        ln = self.lines[self.cy]
        for m in URL_RE.finditer(ln):
            if m.start() <= self.cx < m.end():
                return m.group()
        return None

    def stats(self):
        text = '\n'.join(self.lines)
        words = len(text.split())
        chars = len(text)
        return f"Lines:{len(self.lines)} | Words:{words} | Chars:{chars}"

    def _ensure_view(self, box_h):
        desired_row_from_top = box_h - 1
        if desired_row_from_top < 0:
            desired_row_from_top = 0
        self.view_top = max(0, self.cy - desired_row_from_top)

    def _logical_to_visual_segments(self, text: str, width: int):
        """Return list of (segment_text, start_index_in_logical)."""
        if text == "":
            return [("", 0)]
        segs = []
        start = 0
        while start < len(text):
            seg = text[start:start + width]
            segs.append((seg, start))
            start += width
        return segs

    def draw(self):
        stdscr = self.stdscr
        h, w = stdscr.getmaxyx()
        stdscr.erase()
        title = f" {self.note.title} "
        try:
            stdscr.addstr(0, max(0, (w - len(title)) // 2), title, curses.color_pair(self.colors.get('header', 1)) | curses.A_BOLD)
        except curses.error:
            pass

        outer_x, outer_y = 1, 1
        outer_w = max(40, w - 2)
        outer_h = max(6, h - 4)
        draw_box(stdscr, outer_y, outer_x, outer_h, outer_w, "")
        text_y = outer_y + 1
        text_x = outer_x + 2
        text_h = outer_h - 2
        text_w = max(10, outer_w - 4)

        visual = []
        for li, ln in enumerate(self.lines):
            segs = self._logical_to_visual_segments(ln, text_w)
            for seg_start, seg in [(s, t) for (t, s) in segs]:
                visual.append((li, seg_start, seg))

        vis_row_for_cursor = 0
        vis_col_for_cursor = 0
        found = False
        for vi, (li, seg_start, seg_text) in enumerate(visual):
            if li == self.cy:
                seg_len = len(seg_text)
                if seg_start <= self.cx <= seg_start + seg_len:
                    vis_row_for_cursor = vi
                    vis_col_for_cursor = self.cx - seg_start
                    found = True
                    break
        if not found:
            last_vis = None
            for vi, (li, seg_start, seg_text) in enumerate(visual):
                if li == self.cy:
                    last_vis = (vi, seg_start, seg_text)
            if last_vis is not None:
                vis_row_for_cursor = last_vis[0]
                vis_col_for_cursor = len(last_vis[2])
            else:
                vis_row_for_cursor = 0
                vis_col_for_cursor = 0

        desired_row_from_top = text_h - 1
        self.view_top = max(0, vis_row_for_cursor - desired_row_from_top)

        for i in range(text_h):
            vi = self.view_top + i
            if vi >= len(visual):
                break
            li, seg_start, seg_text = visual[vi]
            try:
                stdscr.addstr(text_y + i, text_x, seg_text)
            except curses.error:
                pass

        # Map visual cursor to screen coordinates, clamp into editor area
        scr_y = text_y + (vis_row_for_cursor - self.view_top)
        scr_x = text_x + vis_col_for_cursor
        min_y, max_y = text_y, text_y + text_h - 1
        min_x, max_x = text_x, text_x + text_w - 1
        sy = min(max(min_y, scr_y), max_y)
        sx = min(max(min_x, scr_x), max_x)

        # status line
        stats = self.stats()
        try:
            stdscr.addstr(outer_y + outer_h, 0, ' ' * (w - 1))
            stdscr.addstr(outer_y + outer_h, 2, stats[:w - 4], curses.color_pair(self.colors.get('status', 2)))
        except curses.error:
            pass

        try:
            curses.curs_set(2)
        except curses.error:
            pass
        try:
            stdscr.move(sy, sx)
        except curses.error:
            try:
                stdscr.move(text_y, text_x)
            except Exception:
                pass

        stdscr.refresh()

    def edit_loop(self):
        self._clamp_cursor()
        while True:
            self.draw()
            k = self.stdscr.getch()
            if k == 27:
                content = '\n'.join(self.lines)
                self.autosave_cb(content)
                return content
            if k == 26:
                self._do_undo(); continue
            if k == 18:
                self._do_redo(); continue
            if k == 22:
                pasted = paste_from_system_clipboard()
                if pasted:
                    self.insert_text(pasted)
                continue
            if k == 23:
                self.delete_prev_word(); continue
            if k == 15:
                url = self.find_url_under_cursor()
                if url:
                    try:
                        curses.endwin()
                        if os.name == 'posix':
                            subprocess.Popen(['xdg-open', url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        elif os.name == 'nt':
                            os.startfile(url)
                    except Exception:
                        pass
                    finally:
                        try:
                            self.stdscr.refresh()
                        except Exception:
                            pass
                continue
            if k in (10, 13):
                self.newline(); continue
            if k in (127, 8, curses.KEY_BACKSPACE):
                self.backspace(); continue
            if k == curses.KEY_LEFT:
                if self.cx > 0:
                    self.cx -= 1
                elif self.cy > 0:
                    self.cy -= 1
                    self.cx = len(self.lines[self.cy])
                continue
            if k == curses.KEY_RIGHT:
                if self.cx < len(self.lines[self.cy]):
                    self.cx += 1
                elif self.cy < len(self.lines) - 1:
                    self.cy += 1
                    self.cx = 0
                continue
            if k == curses.KEY_UP:
                if self.cy > 0:
                    self.cy -= 1
                    self.cx = min(self.cx, len(self.lines[self.cy]))
                continue
            if k == curses.KEY_DOWN:
                if self.cy < len(self.lines) - 1:
                    self.cy += 1
                    self.cx = min(self.cx, len(self.lines[self.cy]))
                continue
            if k == curses.KEY_HOME:
                self.cx = 0; continue
            if k == curses.KEY_END:
                self.cx = len(self.lines[self.cy]); continue
            if 32 <= k <= 126:
                self.insert_text(chr(k)); continue

class Shellpad:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.config = self._load_config()
        self.nb = Notebook(Path(self.config['notebook_file']).expanduser())
        self.nb.load()
        self.selected = 0
        self.top = 0
        self.status = "Welcome to Shellpad! Press ? for help"
        self.internal_copy: Optional[Note] = None
        self.colors = {}
        self.setup_colors()
        self.running = True

    def _load_config(self):
        cfg = DEFAULT_CONFIG.copy()
        if CONFIG_PATH.exists():
            for ln in CONFIG_PATH.read_text(encoding='utf-8').splitlines():
                if ':' in ln:
                    k, v = ln.split(':', 1)
                    cfg[k.strip()] = v.strip()
        return cfg

    def setup_colors(self):
        curses.use_default_colors()
        try:
            curses.init_pair(1, curses.COLOR_MAGENTA, -1)
            curses.init_pair(2, curses.COLOR_YELLOW, -1)
            curses.init_pair(3, curses.COLOR_BLUE, -1)
            curses.init_pair(4, curses.COLOR_CYAN, -1)
            curses.init_pair(5, curses.COLOR_GREEN, -1)
            curses.init_pair(6, curses.COLOR_WHITE, -1)
        except Exception:
            pass
        self.colors = {'header': 1, 'status': 2, 'link': 3, 'list': 4, 'check': 5, 'panel_title': 6}

    def _todo_stats(self, note: Note):
        lines = note.body.splitlines()
        total = 0
        done = 0
        for ln in lines:
            m = re.match(r'^\s*(\[[xX]\]|\[\s?\])', ln)
            if m:
                total += 1
                if re.match(r'^\s*\[[xX]\]', ln):
                    done += 1
        return done, total

    def draw(self):
        stdscr = self.stdscr
        h, w = stdscr.getmaxyx()
        stdscr.erase()
        if w < 40 or h < 10:
            try:
                stdscr.addstr(0, 0, "Terminal too small")
            except curses.error:
                pass
            stdscr.refresh()
            return
        try:
            stdscr.addstr(0, max(0, (w - len("Shellpad")) // 2), "Shellpad", curses.color_pair(self.colors['header']) | curses.A_BOLD)
        except curses.error:
            pass
        list_w = max(28, w // 3)
        draw_box(stdscr, 1, 0, h - 2, list_w + 1, "")
        try:
            stdscr.addstr(1, 2, " Notes ", curses.color_pair(self.colors['panel_title']) | curses.A_BOLD)
        except curses.error:
            pass
        list_h = h - 4
        if self.selected < self.top:
            self.top = self.selected
        if self.selected >= self.top + list_h:
            self.top = self.selected - list_h + 1
        for i, note in enumerate(self.nb.notes[self.top:self.top + list_h]):
            y = 2 + i
            sel = (i + self.top) == self.selected
            selmark = "→ " if sel else "  "
            cap = list_w - 6 - len(selmark)
            title = (note.title[:cap - 1] + '…') if len(note.title) > cap else note.title
            try:
                if sel:
                    stdscr.addnstr(y, 2, f"{selmark}{title}", list_w - 4, curses.color_pair(self.colors['list']) | curses.A_BOLD)
                else:
                    stdscr.addnstr(y, 2, f"{selmark}{title}", list_w - 4)
            except curses.error:
                pass
        pv_x = list_w + 2
        pv_w = w - pv_x - 1
        draw_box(stdscr, 1, pv_x - 1, h - 2, pv_w + 2, "")
        try:
            stdscr.addstr(1, pv_x + 1, " Preview ", curses.color_pair(self.colors['panel_title']) | curses.A_BOLD)
        except curses.error:
            pass
        if self.nb.notes:
            note = self.nb.notes[self.selected]
            preview_h = h - 4
            preview_w = pv_w - 4
            lines = []
            for ln in note.body.splitlines():
                m = TODO_RE.match(ln)
                if m:
                    mark = m.group(1) or ''
                    body = m.group(3) or ''
                    if re.match(r'^\[\s?\]$', mark):
                        conv = f"{self.config.get('doing_symbol', '+')} {body}"
                        checked = False
                    else:
                        conv = f"{self.config.get('done_symbol', '-')} {body}"
                        checked = True
                    wrapped = textwrap.wrap(conv, width=preview_w) or ['']
                    for wln in wrapped:
                        lines.append((wln, checked))
                else:
                    wrapped = textwrap.wrap(ln, width=preview_w) or ['']
                    for wln in wrapped:
                        lines.append((wln, False))
            for i, (ln, checked) in enumerate(lines[:preview_h]):
                try:
                    if ln.startswith(self.config.get('done_symbol', '-')):
                        stdscr.addstr(2 + i, pv_x + 2, ln, curses.color_pair(self.colors['check']) | curses.A_DIM)
                    else:
                        stdscr.addstr(2 + i, pv_x + 2, ln)
                except curses.error:
                    pass
            if len(lines) > preview_h:
                try:
                    stdscr.addstr(2 + preview_h, pv_x + 2, "...", curses.color_pair(self.colors['check']))
                except curses.error:
                    pass
        try:
            stdscr.addstr(h - 1, 0, ' ' * (w - 1))
            stdscr.addstr(h - 1, 1, self.status[:w - 4], curses.color_pair(self.colors['status']))
        except curses.error:
            pass
        stdscr.refresh()

    def open_editor(self, external=False):
        if not self.nb.notes:
            return
        note = self.nb.notes[self.selected]

        def autosave_cb(text):
            self.nb.notes[self.selected] = replace(note, body=text)
            self.nb.save()

        realtime_cfg = self.config.get('realtime_save', 'true').strip().lower()
        realtime_enabled = realtime_cfg in ('1', 'true', 'yes', 'on')

        if external or self.config.get('external_editor', 'false').lower() == 'true':
            editor = self.config.get('default_editor', 'vim')
            try:
                with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".md", encoding='utf-8') as tf:
                    tf.write(note.body)
                    tf.flush()
                    curses.endwin()
                    subprocess.call([editor, tf.name])
                    new_body = open(tf.name, 'r', encoding='utf-8').read()
                os.unlink(tf.name)
                self.nb.notes[self.selected] = replace(note, body=new_body)
                self.nb.save()
                self.status = f"Saved '{note.title}' (external)"
            except Exception as e:
                self.status = f"Editor error: {e}"
            finally:
                try:
                    self.stdscr.refresh()
                except Exception:
                    pass
            return

        editor = Editor(self.stdscr, note, autosave_cb, self.colors, realtime=realtime_enabled)
        new_body = editor.edit_loop()
        self.nb.notes[self.selected] = replace(note, body=new_body)
        self.nb.save()
        self.status = f"Saved '{note.title}'"

    def handle_input(self):
        try:
            k = self.stdscr.getch()
        except (curses.error, KeyboardInterrupt):
            return
        if k == ord('q'):
            self.running = False; return
        if k in (ord('j'), curses.KEY_DOWN):
            self.selected = min(len(self.nb.notes) - 1, self.selected + 1) if self.nb.notes else 0
            self.status = f"Selected: {self.nb.notes[self.selected].title}" if self.nb.notes else self.status
            return
        if k in (ord('k'), curses.KEY_UP):
            self.selected = max(0, self.selected - 1)
            self.status = f"Selected: {self.nb.notes[self.selected].title}"
            return
        if k == ord('a'):
            title = simple_prompt(self.stdscr, "New note title: ")
            if title:
                self.nb.notes.append(Note(title, ""))
                self.nb.save()
                self.selected = len(self.nb.notes) - 1
                self.status = f"Created '{title}'"
            return
        if k in (ord('o'), 10, 13):
            self.open_editor(external=False); return
        if k == ord('O'):
            self.open_editor(external=True); return
        if k == ord('y'):
            if not self.nb.notes:
                self.status = "No notes to copy"; return
            self.internal_copy = replace(self.nb.notes[self.selected])
            self.status = f"Copied '{self.internal_copy.title}' (internal)"; return
        if k == ord('p'):
            if self.internal_copy:
                default = f"{self.internal_copy.title}_copy1"
                name = simple_prompt(self.stdscr, f"Paste as (name) [{default}]: ")
                if name is None:
                    self.status = "Paste cancelled"; return
                if not name.strip():
                    name = default
                self.nb.notes.append(Note(name, self.internal_copy.body))
                self.nb.save()
                self.selected = len(self.nb.notes) - 1
                self.status = f"Pasted as '{name}'"
                return
            if not self.nb.notes:
                self.status = "No notes to paste into"; return
            pasted = paste_from_system_clipboard()
            if pasted:
                n = self.nb.notes[self.selected]
                body = (n.body + '\n' + pasted).lstrip('\n')
                self.nb.notes[self.selected] = replace(n, body=body)
                self.nb.save()
                self.status = "Pasted system clipboard into note"
            else:
                self.status = "System clipboard empty or unavailable"
            return
        if k == ord('Y'):
            if not self.nb.notes:
                self.status = "No notes to copy"; return
            n = self.nb.notes[self.selected]
            ok = copy_to_system_clipboard(n.body)
            if ok:
                self.status = f"Copied '{n.title}' to system clipboard"
            else:
                self.status = "System clipboard not available"
            return
        if k == ord('r'):
            if not self.nb.notes:
                return
            new = simple_prompt(self.stdscr, "Rename to: ")
            if new:
                self.nb.notes[self.selected].title = new
                self.nb.save()
                self.status = f"Renamed to '{new}'"
            return
        if k == ord('d'):
            if not self.nb.notes:
                return
            t = self.nb.notes[self.selected].title
            c = simple_prompt(self.stdscr, f"Delete '{t}'? (y/N): ")
            if c and c.lower() == 'y':
                self.nb.notes.pop(self.selected)
                self.nb.save()
                self.selected = max(0, min(self.selected, len(self.nb.notes) - 1))
                self.status = f"Deleted '{t}'"
            return
        if k == ord('?'):
            show_help(self.stdscr); self.status = "Help closed"; return
        if k == ord('['):
            if self.nb.notes and self.selected > 0:
                idx = self.selected
                self.nb.notes[idx], self.nb.notes[idx - 1] = self.nb.notes[idx - 1], self.nb.notes[idx]
                self.selected -= 1
                self.nb.save()
                self.status = "Moved up"
            return
        if k == ord(']'):
            if self.nb.notes and self.selected < len(self.nb.notes) - 1:
                idx = self.selected
                self.nb.notes[idx], self.nb.notes[idx + 1] = self.nb.notes[idx + 1], self.nb.notes[idx]
                self.selected += 1
                self.nb.save()
                self.status = "Moved down"
            return

    def run(self):
        curses.curs_set(0)
        self.stdscr.keypad(True)
        self.setup_colors()
        self.nb.load()
        startup_note = self.config.get('startup_note', '').strip()
        if startup_note:
            for i, note in enumerate(self.nb.notes):
                if note.title.lower() == startup_note.lower():
                    self.selected = i
                    self.open_editor()
                    break
        while self.running:
            self.draw()
            self.handle_input()

def main(stdscr):
    app = Shellpad(stdscr)
    app.run()

def cli():
    """Command-line entrypoint (used by pip install shellpad)"""
    curses.wrapper(main)

if __name__ == '__main__':
    cli()
