"""Build the two LinkedIn images from the real demo output and the real rulebook.py.

    python3 post/build_images.py

Writes post/night-log.png and post/rulebook.png (1080x1350, rendered at 2x)
using headless Google Chrome.
"""
import html
import io
import keyword
import subprocess
import sys
import tokenize
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from night_shift import run_night  # noqa: E402

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

CSS = """
:root {
  --bg: #0d1117; --card: #161b22; --line: #262c36; --text: #e6edf3; --dim: #8b949e;
  --green: #3fb950; --amber: #e3b341; --red: #f85149;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
html, body { width: 1080px; height: 1350px; background: var(--bg); color: var(--text);
  font-family: -apple-system, "SF Pro Display", "Helvetica Neue", Arial, sans-serif; }
body { padding: 64px 64px 56px; display: flex; flex-direction: column; }
.kicker { font-size: 19px; letter-spacing: .14em; color: var(--dim); font-weight: 600; }
h1 { font-size: 52px; line-height: 1.12; font-weight: 750; margin-top: 18px; letter-spacing: -.01em; }
.sub { font-size: 28px; line-height: 1.35; color: var(--dim); margin-top: 14px; }
.card { background: var(--card); border: 1px solid var(--line); border-radius: 20px; margin-top: 36px; }
.mono { font-family: "SF Mono", Menlo, Consolas, monospace; }
footer { margin-top: auto; padding-top: 22px; display: flex; justify-content: space-between; align-items: baseline;
  font-size: 22px; color: var(--dim); }
footer b { color: var(--text); font-weight: 650; }
"""

LOG_CSS = """
.row { display: grid; grid-template-columns: 74px 148px 1fr; align-items: center;
  padding: 11px 28px; border-top: 1px solid var(--line); }
.row:first-child { border-top: 0; }
.time { font-size: 19px; color: var(--dim); }
.pill { justify-self: start; font-size: 15px; font-weight: 700; letter-spacing: .08em;
  padding: 6px 12px; border-radius: 999px; }
.allow { color: var(--green); background: rgba(63,185,80,.13); }
.ask   { color: var(--amber); background: rgba(227,179,65,.14); }
.deny  { color: var(--red);   background: rgba(248,81,73,.13); }
.what { font-size: 24px; line-height: 1.25; }
.why { font-size: 18px; color: var(--dim); margin-top: 3px; }
.stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-top: 26px; }
.stat { background: var(--card); border: 1px solid var(--line); border-radius: 16px; padding: 16px 22px; }
.stat .n { font-size: 44px; font-weight: 750; line-height: 1; }
.stat .l { font-size: 20px; color: var(--dim); margin-top: 6px; }
"""

CODE_CSS = """
.bar { display: flex; align-items: center; gap: 9px; padding: 16px 22px; border-bottom: 1px solid var(--line); }
.dot { width: 13px; height: 13px; border-radius: 50%; background: #3a404b; }
.bar .name { margin-left: 12px; font-size: 18px; color: var(--dim); }
pre { font-size: 16.5px; line-height: 1.45; padding: 16px 24px 18px 0; counter-reset: ln; }
pre .ln { display: block; padding-left: 64px; position: relative; white-space: pre; }
pre .ln::before { counter-increment: ln; content: counter(ln); position: absolute; left: 0; width: 44px;
  text-align: right; color: #484f58; }
.k { color: #ff7b72; } .s { color: #a5d6ff; } .c { color: #8b949e; font-style: italic; }
.n { color: #79c0ff; } .f { color: #d2a8ff; } .b { color: #ffa657; }
"""

LABELS = {"allow": "DONE", "ask": "WAITING", "deny": "BLOCKED"}
BUILTINS = {"len", "dict", "float", "str", "dataclass", "Path"}


def page(title, extra_css, body):
    return (f"<!doctype html><html><head><meta charset='utf-8'><title>{title}</title>"
            f"<style>{CSS}{extra_css}</style></head><body>{body}</body></html>")


def night_log_html(log, rule_lines):
    rows = "".join(
        f"<div class='row'><span class='time mono'>{e['time']}</span>"
        f"<span class='pill {e['verdict']}'>{LABELS[e['verdict']]}</span>"
        f"<div><div class='what'>{html.escape(e['action'])}</div>"
        f"<div class='why'>{html.escape(e['reason'])}</div></div></div>"
        for e in log)
    count = {v: sum(e["verdict"] == v for e in log) for v in LABELS}
    stats = "".join(
        f"<div class='stat'><div class='n' style='color:var(--{c})'>{count[v]}</div><div class='l'>{l}</div></div>"
        for v, c, l in [("allow", "green", "done on its own"), ("ask", "amber", "waiting for me"),
                        ("deny", "red", "blocked by a rule")])
    body = (f"<div class='kicker'>ALWAYS-ON AGENT · ONE SIMULATED NIGHT · {len(log)} ACTIONS</div>"
            f"<h1>I gave an AI agent the night shift.</h1>"
            f"<div class='sub'>A {rule_lines}-line rulebook decided what it was actually allowed to do.</div>"
            f"<div class='card'>{rows}</div><div class='stats'>{stats}</div>"
            f"<footer><span><b>The model proposes. The rulebook decides.</b></span><span>1 / 2</span></footer>")
    return page("Night shift log", LOG_CSS, body)


def highlight(src):
    """Python source -> HTML, one <span class='ln'> per line, using the stdlib tokenizer."""
    lines = src.splitlines(keepends=True) + ["", ""]  # tokenizer emits end tokens past the last line

    def text(start, end):
        (sr, sc), (er, ec) = start, end
        if sr == er:
            return lines[sr - 1][sc:ec]
        return lines[sr - 1][sc:] + "".join(lines[sr:er - 1]) + lines[er - 1][:ec]

    out, pos, prev = [], (1, 0), ""
    string_types = {tokenize.STRING} | {getattr(tokenize, t) for t in
                                        ("FSTRING_START", "FSTRING_MIDDLE", "FSTRING_END") if hasattr(tokenize, t)}
    for tok in tokenize.generate_tokens(io.StringIO(src).readline):
        if tok.type == tokenize.ENDMARKER:
            break
        out.append(html.escape(text(pos, tok.start)))
        raw = html.escape(text(tok.start, tok.end))
        cls = ""
        if tok.type == tokenize.COMMENT:
            cls = "c"
        elif tok.type in string_types:
            cls = "s"
        elif tok.type == tokenize.NUMBER or tok.string in ("True", "False", "None"):
            cls = "n"
        elif tok.type == tokenize.NAME and keyword.iskeyword(tok.string):
            cls = "k"
        elif tok.type == tokenize.NAME and prev in ("def", "class", "@"):
            cls = "f"
        elif tok.type == tokenize.NAME and tok.string in BUILTINS:
            cls = "b"
        out.append(f"<span class='{cls}'>{raw}</span>" if cls else raw)
        pos, prev = tok.end, tok.string
    return "".join(f"<span class='ln'>{line or ' '}</span>" for line in "".join(out).rstrip("\n").split("\n"))


def rulebook_html(src, tests):
    n = len(src.rstrip("\n").splitlines())
    body = (f"<div class='kicker'>THE WHOLE RULEBOOK</div>"
            f"<h1>{n} lines of plain Python.<br>No model involved.</h1>"
            f"<div class='card'><div class='bar'><span class='dot'></span><span class='dot'></span>"
            f"<span class='dot'></span><span class='name mono'>rulebook.py</span></div>"
            f"<pre class='mono'>{highlight(src)}</pre></div>"
            f"<footer><span><b>{tests} unit tests.</b> Try unit-testing a model's judgment.</span>"
            f"<span>2 / 2</span></footer>")
    return page("Rulebook source", CODE_CSS, body)


def render(html_path, png_path):
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                    "--force-device-scale-factor=2", "--window-size=1080,1350",
                    f"--screenshot={png_path}", html_path.as_uri()],
                   check=True, capture_output=True)


if __name__ == "__main__":
    src = (ROOT / "rulebook.py").read_text()
    tests = (ROOT / "test_rulebook.py").read_text().count("    def test_")
    pages = {"night-log": night_log_html(run_night(), len(src.rstrip("\n").splitlines())),
             "rulebook": rulebook_html(src, tests)}
    for name, doc in pages.items():
        html_path = HERE / f"{name}.html"
        html_path.write_text(doc)
        render(html_path, HERE / f"{name}.png")
        print(f"wrote post/{name}.png")
