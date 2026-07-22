from __future__ import annotations

import json
import math
import os
import sys
import urllib.error
import urllib.request
from collections import Counter
from datetime import UTC, datetime, timedelta
from html import escape
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

API_ROOT = "https://api.github.com"
USERNAME = os.getenv("PROFILE_USERNAME", "Conroy1988")
ORGANISATION = os.getenv("PROFILE_ORGANISATION", "Team-Killing-Bastards")
UTC_OFFSET = int(os.getenv("PROFILE_UTC_OFFSET", "1"))
OUTPUT_DIR = Path("assets/profile-cards")
README = Path("README.md")
FIRST_PARTY_SYSTEMS = 6
TKB_ACTIVE_SYSTEMS = 4
OWNER_DOMAINS = 3

PALETTE = {
    "JavaScript": "#f7df1e",
    "TypeScript": "#3178c6",
    "Python": "#3776ab",
    "HTML": "#e34f26",
    "CSS": "#1572b6",
    "PowerShell": "#5391fe",
    "Shell": "#89e051",
    "C#": "#178600",
    "C++": "#f34b7d",
    "Vue": "#41b883",
    "Other": "#7b6cf6",
}
FALLBACK_COLORS = ["#7b6cf6", "#45e0ef", "#d866ef", "#22d3a6", "#ca8a04"]


def api_get(path: str) -> Any:
    token = os.getenv("GITHUB_TOKEN", "").strip()
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": f"{USERNAME}-profile-card-generator",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(f"{API_ROOT}{path}", headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def language_color(name: str, index: int = 0) -> str:
    return PALETTE.get(name, FALLBACK_COLORS[index % len(FALLBACK_COLORS)])


def safe_number(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def collect_profile_data() -> dict[str, Any]:
    profile = api_get(f"/users/{USERNAME}")
    personal_repos = api_get(
        f"/users/{USERNAME}/repos?per_page=100&type=owner&sort=updated&direction=desc"
    )
    organisation_repos = api_get(
        f"/orgs/{ORGANISATION}/repos?per_page=100&type=public&sort=updated&direction=desc"
    )
    events = api_get(f"/users/{USERNAME}/events/public?per_page=100")

    source_repos: list[dict[str, Any]] = []
    seen: set[str] = set()
    for repo in [*personal_repos, *organisation_repos]:
        full_name = str(repo.get("full_name", ""))
        if not full_name or full_name in seen:
            continue
        seen.add(full_name)
        if repo.get("fork") or repo.get("archived"):
            continue
        if repo.get("name") in {USERNAME, ".github", "demo-repository"}:
            continue
        source_repos.append(repo)

    repo_languages: Counter[str] = Counter()
    byte_languages: Counter[str] = Counter()
    for repo in source_repos:
        primary = repo.get("language")
        if isinstance(primary, str) and primary:
            repo_languages[primary] += 1
        full_name = str(repo.get("full_name", ""))
        try:
            language_payload = api_get(f"/repos/{full_name}/languages")
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
            continue
        if isinstance(language_payload, dict):
            for language, amount in language_payload.items():
                byte_languages[str(language)] += safe_number(amount)

    now = datetime.now(UTC)
    cutoff = now - timedelta(days=30)
    recent_events: list[dict[str, Any]] = []
    hourly = [0] * 24
    event_types: Counter[str] = Counter()
    for event in events:
        created_at = str(event.get("created_at", ""))
        try:
            when = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        except ValueError:
            continue
        local_when = when + timedelta(hours=UTC_OFFSET)
        hourly[local_when.hour] += 1
        if when >= cutoff:
            recent_events.append(event)
            event_types[str(event.get("type", "Other"))] += 1

    pull_request_activity = sum(
        event_types[name]
        for name in (
            "PullRequestEvent",
            "PullRequestReviewEvent",
            "PullRequestReviewCommentEvent",
        )
    )
    issue_activity = event_types["IssuesEvent"] + event_types["IssueCommentEvent"]

    return {
        "public_repositories": safe_number(profile.get("public_repos"), len(personal_repos)),
        "repo_languages": repo_languages,
        "byte_languages": byte_languages,
        "events_30d": len(recent_events),
        "push_events": event_types["PushEvent"],
        "pull_request_activity": pull_request_activity,
        "issue_activity": issue_activity,
        "hourly": hourly,
        "updated_at": now,
    }


def fallback_data() -> dict[str, Any]:
    return {
        "public_repositories": 6,
        "repo_languages": Counter({"JavaScript": 2, "Python": 1, "TypeScript": 1}),
        "byte_languages": Counter({"JavaScript": 58, "Python": 28, "TypeScript": 10, "CSS": 4}),
        "events_30d": 0,
        "push_events": 0,
        "pull_request_activity": 0,
        "issue_activity": 0,
        "hourly": [0] * 24,
        "updated_at": datetime.now(UTC),
    }


def svg_shell(width: int, height: int, title: str, subtitle: str, body: str) -> str:
    safe_title = escape(title)
    safe_subtitle = escape(subtitle)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="card-title card-desc">
  <title id="card-title">{safe_title}</title>
  <desc id="card-desc">{safe_subtitle}</desc>
  <defs>
    <linearGradient id="background" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#0d1117"/>
      <stop offset="0.55" stop-color="#151827"/>
      <stop offset="1" stop-color="#101522"/>
    </linearGradient>
    <linearGradient id="accent" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#45e0ef"/>
      <stop offset="0.5" stop-color="#7b6cf6"/>
      <stop offset="1" stop-color="#d866ef"/>
    </linearGradient>
  </defs>
  <rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="18" fill="url(#background)" stroke="#30363d" stroke-width="2"/>
  <rect x="1" y="1" width="{width - 2}" height="5" rx="3" fill="url(#accent)"/>
  <circle cx="29" cy="36" r="7" fill="#45e0ef"/>
  <text x="48" y="43" fill="#70a5fd" font-family="Segoe UI, Arial, sans-serif" font-size="22" font-weight="700">{safe_title}</text>
  <text x="28" y="67" fill="#a9b1d6" font-family="Segoe UI, Arial, sans-serif" font-size="12">{safe_subtitle}</text>
{body}
</svg>
'''


def metric_tile(x: int, label: str, value: str, detail: str, accent: str) -> str:
    return f'''  <rect x="{x}" y="91" width="190" height="116" rx="14" fill="#161b22" stroke="#30363d"/>
  <rect x="{x}" y="91" width="5" height="116" rx="3" fill="{accent}"/>
  <text x="{x + 20}" y="123" fill="#8b949e" font-family="Segoe UI, Arial, sans-serif" font-size="12" font-weight="600">{escape(label.upper())}</text>
  <text x="{x + 20}" y="169" fill="{accent}" font-family="Segoe UI, Arial, sans-serif" font-size="38" font-weight="800">{escape(value)}</text>
  <text x="{x + 20}" y="193" fill="#c9d1d9" font-family="Segoe UI, Arial, sans-serif" font-size="11">{escape(detail)}</text>'''


def overview_svg(data: dict[str, Any]) -> str:
    updated = data["updated_at"].strftime("%d %b %Y · %H:%M UTC")
    body = "\n".join(
        [
            metric_tile(28, "Public repositories", str(data["public_repositories"]), "Visible GitHub repositories", "#45e0ef"),
            metric_tile(238, "First-party systems", str(FIRST_PARTY_SYSTEMS), "Owned and actively developed", "#7b6cf6"),
            metric_tile(448, "TKB systems", str(TKB_ACTIVE_SYSTEMS), "Active organisation products", "#d866ef"),
            metric_tile(658, "Owner domains", str(OWNER_DOMAINS), "TKB · Conroy · Marty", "#22d3a6"),
            f'''  <circle cx="31" cy="235" r="5" fill="#22d3a6"/>
  <text x="44" y="239" fill="#8b949e" font-family="Segoe UI, Arial, sans-serif" font-size="11">Repository-owned card · generated from the GitHub API · {escape(updated)}</text>''',
        ]
    )
    return svg_shell(880, 260, "Profile Operations Snapshot", "Public portfolio posture without third-party card rendering", body)


def top_items(counter: Counter[str], limit: int = 5) -> list[tuple[str, int]]:
    items = [(name, amount) for name, amount in counter.most_common(limit) if amount > 0]
    return items or [("No public data", 1)]


def language_repo_svg(data: dict[str, Any]) -> str:
    items = top_items(data["repo_languages"], 5)
    maximum = max(amount for _, amount in items)
    rows: list[str] = []
    for index, (name, amount) in enumerate(items):
        y = 94 + index * 31
        width = max(8, int(250 * amount / maximum))
        color = language_color(name, index)
        rows.append(
            f'''  <text x="28" y="{y + 11}" fill="#c9d1d9" font-family="Segoe UI, Arial, sans-serif" font-size="12">{escape(name)}</text>
  <rect x="126" y="{y}" width="260" height="13" rx="6" fill="#21262d"/>
  <rect x="126" y="{y}" width="{width}" height="13" rx="6" fill="{color}"/>
  <text x="400" y="{y + 11}" text-anchor="end" fill="{color}" font-family="Segoe UI, Arial, sans-serif" font-size="12" font-weight="700">{amount}</text>'''
        )
    return svg_shell(430, 270, "Languages by Repository", "Primary language across public first-party source repositories", "\n".join(rows))


def ring_segments(items: list[tuple[str, int]], cx: int, cy: int, radius: int) -> str:
    total = sum(value for _, value in items) or 1
    circumference = 2 * math.pi * radius
    offset = 0.0
    segments: list[str] = []
    for index, (name, value) in enumerate(items):
        length = circumference * value / total
        color = language_color(name, index)
        segments.append(
            f'''  <circle cx="{cx}" cy="{cy}" r="{radius}" fill="none" stroke="{color}" stroke-width="20" stroke-dasharray="{length:.2f} {circumference - length:.2f}" stroke-dashoffset="{-offset:.2f}" transform="rotate(-90 {cx} {cy})"/>'''
        )
        offset += length
    return "\n".join(segments)


def language_volume_svg(data: dict[str, Any]) -> str:
    raw_items = top_items(data["byte_languages"], 4)
    total_all = sum(data["byte_languages"].values()) or sum(value for _, value in raw_items)
    shown = sum(value for _, value in raw_items)
    items = list(raw_items)
    if total_all > shown:
        items.append(("Other", total_all - shown))
    total = sum(value for _, value in items) or 1
    legends: list[str] = []
    for index, (name, value) in enumerate(items):
        y = 104 + index * 28
        color = language_color(name, index)
        percentage = value / total * 100
        legends.append(
            f'''  <rect x="244" y="{y - 10}" width="11" height="11" rx="2" fill="{color}"/>
  <text x="264" y="{y}" fill="#c9d1d9" font-family="Segoe UI, Arial, sans-serif" font-size="12">{escape(name)}</text>
  <text x="400" y="{y}" text-anchor="end" fill="{color}" font-family="Segoe UI, Arial, sans-serif" font-size="12" font-weight="700">{percentage:.0f}%</text>'''
        )
    body = f'''  <circle cx="120" cy="166" r="58" fill="none" stroke="#21262d" stroke-width="20"/>
{ring_segments(items, 120, 166, 58)}
  <circle cx="120" cy="166" r="37" fill="#151827"/>
  <text x="120" y="161" text-anchor="middle" fill="#f0f6fc" font-family="Segoe UI, Arial, sans-serif" font-size="22" font-weight="800">{len(items)}</text>
  <text x="120" y="180" text-anchor="middle" fill="#8b949e" font-family="Segoe UI, Arial, sans-serif" font-size="10">LANGUAGES</text>
{chr(10).join(legends)}'''
    return svg_shell(430, 270, "Languages by Code Volume", "Aggregated public source bytes reported by GitHub", body)


def activity_svg(data: dict[str, Any]) -> str:
    metrics = [
        ("PUBLIC EVENTS", data["events_30d"], "last 30 days", "#45e0ef"),
        ("PUSH EVENTS", data["push_events"], "public activity", "#7b6cf6"),
        ("PR / REVIEWS", data["pull_request_activity"], "public activity", "#d866ef"),
        ("ISSUES / COMMENTS", data["issue_activity"], "public activity", "#22d3a6"),
    ]
    blocks: list[str] = []
    for index, (label, value, detail, color) in enumerate(metrics):
        column = index % 2
        row = index // 2
        x = 28 + column * 194
        y = 91 + row * 77
        blocks.append(
            f'''  <rect x="{x}" y="{y}" width="176" height="65" rx="12" fill="#161b22" stroke="#30363d"/>
  <text x="{x + 15}" y="{y + 22}" fill="#8b949e" font-family="Segoe UI, Arial, sans-serif" font-size="10" font-weight="700">{label}</text>
  <text x="{x + 15}" y="{y + 50}" fill="{color}" font-family="Segoe UI, Arial, sans-serif" font-size="25" font-weight="800">{value}</text>
  <text x="{x + 56}" y="{y + 49}" fill="#8b949e" font-family="Segoe UI, Arial, sans-serif" font-size="10">{detail}</text>'''
        )
    return svg_shell(430, 270, "Public Development Activity", "Recent public GitHub events; private work is intentionally excluded", "\n".join(blocks))


def productive_time_svg(data: dict[str, Any]) -> str:
    hourly = list(data["hourly"])
    maximum = max(hourly) if any(hourly) else 1
    chart_x = 30
    chart_y = 220
    chart_height = 120
    bar_step = 15
    bars: list[str] = []
    peak = max(range(24), key=lambda hour: hourly[hour]) if any(hourly) else 0
    for hour, value in enumerate(hourly):
        height = 0 if value == 0 else max(4, int(chart_height * value / maximum))
        x = chart_x + hour * bar_step
        y = chart_y - height
        color = "#45e0ef" if hour == peak and value else "#a371f7"
        opacity = "1" if value else "0.18"
        bars.append(
            f'''  <rect x="{x}" y="{y}" width="10" height="{height if height else 2}" rx="3" fill="{color}" opacity="{opacity}"/>'''
        )
    labels = "".join(
        f'''  <text x="{chart_x + hour * bar_step + 5}" y="242" text-anchor="middle" fill="#8b949e" font-family="Segoe UI, Arial, sans-serif" font-size="9">{hour}</text>'''
        for hour in (0, 6, 12, 18, 23)
    )
    peak_label = f"Peak public activity: {peak:02d}:00–{(peak + 1) % 24:02d}:00" if any(hourly) else "Awaiting public event data"
    body = f'''  <line x1="28" y1="220" x2="392" y2="220" stroke="#30363d"/>
  <line x1="28" y1="100" x2="28" y2="220" stroke="#30363d"/>
{chr(10).join(bars)}
{labels}
  <text x="28" y="260" fill="#45e0ef" font-family="Segoe UI, Arial, sans-serif" font-size="10">{escape(peak_label)}</text>'''
    return svg_shell(430, 270, f"Activity Rhythm · UTC {UTC_OFFSET:+d}", "Distribution of the latest public GitHub events by local hour", body)


def write_svg(path: Path, content: str) -> None:
    ElementTree.fromstring(content)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def patch_readme() -> bool:
    if not README.exists():
        return False
    text = README.read_text(encoding="utf-8")
    external_start = '<img width="95%" src="https://github-profile-summary-cards.vercel.app/api/cards/profile-details'
    local_start = '<img width="95%" src="./assets/profile-cards/overview.svg"'
    replacement = '''<img width="95%" src="./assets/profile-cards/overview.svg" alt="Conroy1988 repository-owned profile operations snapshot">\n\n<img width="47%" src="./assets/profile-cards/languages-repos.svg" alt="Languages across Conroy1988 public first-party repositories">\n<img width="47%" src="./assets/profile-cards/languages-volume.svg" alt="Language code volume across Conroy1988 public first-party repositories">\n\n<img width="47%" src="./assets/profile-cards/public-activity.svg" alt="Conroy1988 recent public GitHub activity">\n<img width="47%" src="./assets/profile-cards/activity-rhythm.svg" alt="Conroy1988 public GitHub activity rhythm">'''

    changed = False
    if external_start in text:
        start = text.index(external_start)
        end_marker = '<img width="47%" src="https://github-profile-summary-cards.vercel.app/api/cards/productive-time'
        end = text.index(end_marker, start)
        end = text.index(">", end) + 1
        text = text[:start] + replacement + text[end:]
        changed = True
    elif local_start not in text:
        raise RuntimeError("GitHub Activity card block could not be located safely")

    old_note = "These panels represent public GitHub activity. Private repositories, private runner work, and some organisation contributions are not fully visible through public profile APIs."
    new_note = "These repository-owned cards are regenerated daily from GitHub's API. Private repositories, private runner work, and some organisation contributions remain intentionally outside public profile statistics."
    if old_note in text:
        text = text.replace(old_note, new_note)
        changed = True

    if changed:
        README.write_text(text, encoding="utf-8", newline="\n")
    return changed


def main() -> int:
    try:
        data = collect_profile_data()
        source = "GitHub API"
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as error:
        print(f"GitHub API unavailable; generating safe fallback cards: {error}", file=sys.stderr)
        data = fallback_data()
        source = "fallback"

    write_svg(OUTPUT_DIR / "overview.svg", overview_svg(data))
    write_svg(OUTPUT_DIR / "languages-repos.svg", language_repo_svg(data))
    write_svg(OUTPUT_DIR / "languages-volume.svg", language_volume_svg(data))
    write_svg(OUTPUT_DIR / "public-activity.svg", activity_svg(data))
    write_svg(OUTPUT_DIR / "activity-rhythm.svg", productive_time_svg(data))
    patched = patch_readme()
    print(f"Generated repository-owned profile cards from {source}; README patched={patched}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
