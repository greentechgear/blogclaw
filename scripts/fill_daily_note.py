#!/usr/bin/env python3
"""
BlogClaw: Fill Daily Note
Populates /workspace/group/blogging/Daily/YYYY-MM-DD.md with real activity data.

Sources used:
  - WordPress API (brianchappell.com + consultdex.com) — posts published today
  - DAILY_ACTIVITY_LOG.md — revision analysis for today
  - conversations/ — session summaries for today
  - CodeLog (global knowledge vault) — code written today
  - message-bus.json — cross-channel activity today

Run: python3 fill_daily_note.py [--date YYYY-MM-DD] [--learning-dir /path]
Called by the 11 PM BlogClaw heartbeat task.
"""

import os
import sys
import re
import json
import argparse
from pathlib import Path
from datetime import datetime, timezone, timedelta

import requests
from requests.auth import HTTPBasicAuth

# ── Paths ──────────────────────────────────────────────────────────────────
GROUP_DIR     = Path(__file__).resolve().parent.parent.parent   # tg-blogging-*/
VAULT_ROOT    = Path("/root/nanoclaw/groups/tg-nanobot-research-1003715687564/knowledge")
CODELOG_DIR   = VAULT_ROOT / "Knowledge" / "CodeLog"
MESSAGE_BUS   = Path("/root/nanoclaw/groups/global/channels/message-bus.json")

WP_SITES = [
    {
        "name":    "brianchappell.com",
        "api":     "https://brianchappell.com/wp-json/wp/v2",
        "env_user":"WORDPRESS_USER",
        "env_pass":"WORDPRESS_PASSWORD",
    },
    {
        "name":    "consultdex.com",
        "api":     "https://consultdex.com/wp-json/wp/v2",
        "env_user":"CONSULTDEX_USER",
        "env_pass":"CONSULTDEX_PASSWORD",
    },
]


def load_env(group_dir: Path) -> dict:
    env = {}
    env_path = group_dir / ".env"
    if not env_path.is_file():
        env_path = group_dir / "blogclaw" / ".env"
    if env_path.is_file():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    # Also pull live env
    for k in ["WORDPRESS_USER", "WORDPRESS_PASSWORD", "CONSULTDEX_USER", "CONSULTDEX_PASSWORD"]:
        if k in os.environ:
            env[k] = os.environ[k]
    return env


# ── Data collectors ─────────────────────────────────────────────────────────

def fetch_published_today(site: dict, env: dict, date_str: str) -> list[dict]:
    user = env.get(site["env_user"], "")
    pwd  = env.get(site["env_pass"], "")
    if not user or not pwd:
        return []
    results = []
    for kind in ("posts", "pages"):
        try:
            url = f"{site['api']}/{kind}?per_page=50&orderby=date&order=desc&status=publish"
            resp = requests.get(url, auth=HTTPBasicAuth(user, pwd), timeout=20)
            if resp.status_code != 200:
                continue
            for item in resp.json():
                pub = item.get("date", "")[:10]
                mod = item.get("modified", "")[:10]
                if pub == date_str or mod == date_str:
                    title = item.get("title", {}).get("rendered", "")
                    title = re.sub(r"<[^>]+>", "", title)
                    results.append({
                        "title": title,
                        "url":   item.get("link", ""),
                        "time":  item.get("date", "")[11:16],
                        "kind":  kind.rstrip("s"),
                        "action": "published" if pub == date_str else "updated",
                    })
        except Exception:
            continue
    return results


def extract_daily_activity_log(learning_dir: Path, date_str: str) -> str:
    """Pull today's section from DAILY_ACTIVITY_LOG.md if it exists."""
    log_path = learning_dir / "DAILY_ACTIVITY_LOG.md"
    if not log_path.is_file():
        return ""
    text = log_path.read_text()
    pattern = rf"## {date_str}.*?(?=\n## 20|\Z)"
    m = re.search(pattern, text, re.DOTALL)
    if not m:
        return ""
    section = m.group(0).strip()
    # Strip the heading itself, keep body
    lines = section.splitlines()[1:]
    return "\n".join(lines).strip()


def read_conversations_today(group_dir: Path, date_str: str) -> list[str]:
    """Scan conversations/ for files from today and extract key lines."""
    conv_dir = group_dir / "conversations"
    if not conv_dir.is_dir():
        return []
    summaries = []
    for f in sorted(conv_dir.iterdir()):
        if date_str in f.name and f.suffix == ".md":
            text = f.read_text(errors="replace")
            # Grab first non-empty non-heading line as summary
            for line in text.splitlines():
                line = line.strip()
                if line and not line.startswith("#") and len(line) > 20:
                    summaries.append(line[:120])
                    break
    return summaries


def read_codelog_today(date_str: str) -> list[dict]:
    """Read today's CodeLog entries."""
    log_file = CODELOG_DIR / f"{date_str}.md"
    if not log_file.is_file():
        return []
    entries = []
    current = {}
    for line in log_file.read_text().splitlines():
        m = re.match(r"^## \[(\w+)\] `(.+?)` — (.+)", line)
        if m:
            if current:
                entries.append(current)
            current = {"action": m.group(1), "file": m.group(2), "channel": m.group(3)}
        elif line.startswith("- **Description:**") and current:
            current["desc"] = line.replace("- **Description:**", "").strip()
    if current:
        entries.append(current)
    return entries


def read_bus_activity(date_str: str) -> list[str]:
    """Grab cross-channel messages from today."""
    if not MESSAGE_BUS.is_file():
        return []
    try:
        bus = json.loads(MESSAGE_BUS.read_text())
    except Exception:
        return []
    items = []
    for msg in bus.get("messages", []):
        ts = msg.get("timestamp", "")
        if ts[:10] == date_str:
            items.append(
                f"{msg.get('from','?')} → {msg.get('to','?')}: {msg.get('subject','')}"
            )
    return items


# ── Template filler ─────────────────────────────────────────────────────────

def fill_template(
    date_str: str,
    date_display: str,
    published: dict,          # {site_name: [items]}
    activity_log: str,
    conversations: list[str],
    code_entries: list[dict],
    bus_activity: list[str],
) -> str:

    def bullet(items, indent="- "):
        return "\n".join(f"{indent}{i}" for i in items) if items else f"{indent}(none)"

    # ── Content Work section ────────────────────────────────────────────────
    content_lines = []
    total_posts = 0
    for site, items in published.items():
        if items:
            content_lines.append(f"\n**{site}:**")
            for it in items:
                content_lines.append(
                    f"- [{it['title']}]({it['url']}) — {it['action']} {it['time']} UTC"
                )
            total_posts += len(items)
    if not content_lines:
        content_lines = ["- No posts published today"]

    # ── System Work section ─────────────────────────────────────────────────
    system_lines = []
    if code_entries:
        system_lines.append("**Code written/modified:**")
        for e in code_entries[:15]:
            system_lines.append(
                f"- [{e.get('action','?')}] `{e.get('file','?')}` ({e.get('channel','?')}) — {e.get('desc','')[:80]}"
            )
    if bus_activity:
        system_lines.append("\n**Cross-channel activity:**")
        for a in bus_activity[:10]:
            system_lines.append(f"- {a}")
    if not system_lines:
        system_lines = ["- No system changes logged today"]

    # ── Learning sections from DAILY_ACTIVITY_LOG ──────────────────────────
    learning_block = activity_log if activity_log else "(run heartbeat_daily.py to populate)"

    # ── Conversations ───────────────────────────────────────────────────────
    conv_block = bullet(conversations) if conversations else "- No sessions logged today"

    # ── Metrics ─────────────────────────────────────────────────────────────
    bc_count   = len([i for items in published.values() for i in items if "brianchappell" in i.get("url","") or "brianchappell" in str(i)])
    cdex_count = len([i for items in published.values() for i in items if "consultdex" in i.get("url","") or "consultdex" in str(i)])

    next_date = (datetime.strptime(date_str, "%Y-%m-%d") + timedelta(days=1)).strftime("%B %d, %Y")

    note = f"""# Daily Note - {date_display}

## My Activity

### Content Work
{chr(10).join(content_lines)}

### System Work
{chr(10).join(system_lines)}

### Client/Business
- Cross-channel messages today: {len(bus_activity)}
{conv_block if conversations else "- No client sessions logged"}

## Learning

### From Today's Activity
{learning_block}

### What Worked
- (Review DAILY_ACTIVITY_LOG.md for patterns)

### What Didn't Work
- (Review DAILY_ACTIVITY_LOG.md for issues)

### Key Insights
- (To be filled in during or after sessions)

### Technical Learnings
- Code files changed today: {len(code_entries)}
{chr(10).join([f"  - `{e.get('file','?')}`: {e.get('desc','')[:60]}" for e in code_entries[:5]])}

## Tomorrow

### Immediate Tasks
- [ ] Priority 1
- [ ] Priority 2
- [ ] Priority 3

### Content Pipeline
- [ ] Blog ideas to develop
- [ ] Research needed
- [ ] Posts to draft/publish

### System Improvements
- [ ] Technical fixes needed
- [ ] Workflow enhancements
- [ ] Documentation to create

## Metrics

**Content Created:** {total_posts} post(s)
**brianchappell.com published:** {len(published.get('brianchappell.com', []))}
**consultdex.com published:** {len(published.get('consultdex.com', []))}
**Code files touched:** {len(code_entries)}
**Cross-channel messages:** {len(bus_activity)}
**Voice Quality:** (to be assessed)
**System Health:** (green/yellow/red)

---

*Next Daily Note: {next_date}*
*Auto-generated by fill_daily_note.py — edit freely*
"""
    return note


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Fill today's daily note with real activity data.")
    parser.add_argument("--date",         default="",
                        help="Date to fill (YYYY-MM-DD). Defaults to today UTC.")
    parser.add_argument("--learning-dir", default="",
                        help="Path to learning dir containing DAILY_ACTIVITY_LOG.md. "
                             "Defaults to <group>/blogging/")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print filled note to stdout instead of writing file.")
    args = parser.parse_args()

    date_str = args.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    date_display = datetime.strptime(date_str, "%Y-%m-%d").strftime("%B %d, %Y")

    learning_dir = Path(args.learning_dir) if args.learning_dir else (GROUP_DIR / "blogging")
    daily_dir    = learning_dir / "Daily"
    out_file     = daily_dir / f"{date_str}.md"

    env = load_env(GROUP_DIR)

    print(f"Filling daily note for {date_str}...")

    # Gather data
    published = {}
    for site in WP_SITES:
        items = fetch_published_today(site, env, date_str)
        published[site["name"]] = items
        print(f"  {site['name']}: {len(items)} item(s) found")

    activity_log  = extract_daily_activity_log(learning_dir, date_str)
    conversations = read_conversations_today(GROUP_DIR, date_str)
    code_entries  = read_codelog_today(date_str)
    bus_activity  = read_bus_activity(date_str)

    print(f"  DAILY_ACTIVITY_LOG section: {'found' if activity_log else 'not yet (run after 11PM task)'}")
    print(f"  Conversations today: {len(conversations)}")
    print(f"  Code entries today: {len(code_entries)}")
    print(f"  Cross-channel messages: {len(bus_activity)}")

    note = fill_template(
        date_str=date_str,
        date_display=date_display,
        published=published,
        activity_log=activity_log,
        conversations=conversations,
        code_entries=code_entries,
        bus_activity=bus_activity,
    )

    if args.dry_run:
        print("\n" + "=" * 60)
        print(note)
        return

    daily_dir.mkdir(parents=True, exist_ok=True)
    out_file.write_text(note, encoding="utf-8")
    print(f"\n✓ Daily note written: {out_file}")

    # Also log this action to the code log
    try:
        os.system(
            f'python3 /root/nanoclaw/groups/global/skills/log_code.py '
            f'--channel blogging '
            f'--file "{out_file}" '
            f'--description "Daily note for {date_str} — auto-filled by fill_daily_note.py" '
            f'--action modified --no-snippet'
        )
    except Exception:
        pass


if __name__ == "__main__":
    main()
