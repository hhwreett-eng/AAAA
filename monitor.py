#!/usr/bin/env python3
"""
Public content monitor for tech/investing creators.

The monitor intentionally uses public feeds, ordinary public pages, and optional
official APIs. It does not try to bypass login walls, paywalls, robots controls,
or anti-bot systems.
"""

from __future__ import annotations

import argparse
import datetime as dt
import email.utils
import hashlib
import html
import json
import os
import re
import smtplib
import sys
import textwrap
import time
import tomllib
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from email.message import EmailMessage
from pathlib import Path
from typing import Any

from docx import Document
from docx.shared import Pt


APP_NAME = "tech-influencer-monitor"
DEFAULT_CONFIG = "config.toml"
USER_AGENT = (
    "Mozilla/5.0 (compatible; TechInfluencerMonitor/1.0; "
    "+https://example.local/monitor)"
)


@dataclass
class MonitorItem:
    creator: str
    source_name: str
    source_id: str
    source_type: str
    title: str
    url: str
    published_at: dt.datetime | None
    fetched_at: dt.datetime
    summary: str = ""
    tags: list[str] = field(default_factory=list)
    matched_keywords: list[str] = field(default_factory=list)
    item_id: str = ""


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def read_config(path: Path) -> dict[str, Any]:
    with path.open("rb") as f:
        return tomllib.load(f)


def ensure_dirs(*paths: Path) -> None:
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"seen": {}, "page_hashes": {}}
    with path.open("r", encoding="utf-8") as f:
        state = json.load(f)
    state.setdefault("seen", {})
    state.setdefault("page_hashes", {})
    return state


def save_state(path: Path, state: dict[str, Any]) -> None:
    temp = path.with_suffix(".tmp")
    with temp.open("w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2, sort_keys=True)
    temp.replace(path)


def fetch_url(url: str, timeout: int = 25, headers: dict[str, str] | None = None) -> tuple[bytes, str]:
    request_headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, text/html;q=0.9, */*;q=0.8",
    }
    if headers:
        request_headers.update(headers)
    req = urllib.request.Request(url, headers=request_headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read()
        final_url = resp.geturl()
    return body, final_url


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def children(elem: ET.Element, name: str) -> list[ET.Element]:
    wanted = name.lower()
    return [child for child in list(elem) if local_name(child.tag) == wanted]


def first_child(elem: ET.Element, *names: str) -> ET.Element | None:
    wanted = {name.lower() for name in names}
    for child in list(elem):
        if local_name(child.tag) in wanted:
            return child
    return None


def first_text(elem: ET.Element, *names: str) -> str:
    child = first_child(elem, *names)
    if child is None or child.text is None:
        return ""
    return clean_text(child.text)


def clean_text(value: str, max_len: int = 500) -> str:
    value = html.unescape(value)
    value = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", value)
    value = re.sub(r"(?s)<[^>]+>", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    if len(value) > max_len:
        return value[: max_len - 1].rstrip() + "…"
    return value


def parse_datetime(value: str) -> dt.datetime | None:
    value = (value or "").strip()
    if not value:
        return None

    try:
        parsed = email.utils.parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.timezone.utc)
        return parsed.astimezone(dt.timezone.utc)
    except (TypeError, ValueError, IndexError, OverflowError):
        pass

    candidates = [
        value,
        value.replace("Z", "+00:00"),
        re.sub(r"\.\d+", "", value).replace("Z", "+00:00"),
    ]
    for candidate in candidates:
        try:
            parsed = dt.datetime.fromisoformat(candidate)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=dt.timezone.utc)
            return parsed.astimezone(dt.timezone.utc)
        except ValueError:
            continue
    return None


def item_key(source_id: str, item_id: str) -> str:
    raw = f"{source_id}|{item_id}".encode("utf-8", errors="ignore")
    return hashlib.sha256(raw).hexdigest()


def stable_item_id(url: str, title: str, published_at: dt.datetime | None) -> str:
    if url:
        return url
    published = published_at.isoformat() if published_at else ""
    return hashlib.sha256(f"{title}|{published}".encode("utf-8")).hexdigest()


def match_keywords(text: str, keywords: list[str]) -> list[str]:
    text_lower = text.lower()
    found = []
    for keyword in keywords:
        keyword = keyword.strip()
        if keyword and keyword.lower() in text_lower:
            found.append(keyword)
    return found


def parse_feed(
    body: bytes,
    source: dict[str, Any],
    creator_name: str,
    creator_tags: list[str],
) -> list[MonitorItem]:
    try:
        root = ET.fromstring(body)
    except ET.ParseError as exc:
        raise ValueError(f"feed XML parse failed: {exc}") from exc

    source_id = source.get("id") or source.get("name") or source.get("url")
    source_name = source.get("name", source_id)
    fetched_at = utc_now()
    items: list[MonitorItem] = []

    if local_name(root.tag) == "rss":
        channel = first_child(root, "channel")
        if channel is None:
            channel = root
        entries = children(channel, "item")
        for entry in entries:
            title = first_text(entry, "title") or "(untitled)"
            link = first_text(entry, "link")
            guid = first_text(entry, "guid")
            published_at = parse_datetime(
                first_text(entry, "pubDate", "published", "updated", "dc:date")
            )
            summary = first_text(entry, "description", "summary", "content")
            final_id = stable_item_id(link or guid, title, published_at)
            items.append(
                MonitorItem(
                    creator=creator_name,
                    source_name=source_name,
                    source_id=source_id,
                    source_type="feed",
                    title=title,
                    url=link or guid or source.get("url", ""),
                    published_at=published_at,
                    fetched_at=fetched_at,
                    summary=summary,
                    tags=creator_tags + list(source.get("tags", [])),
                    item_id=final_id,
                )
            )
        return items

    entries = children(root, "entry")
    for entry in entries:
        title = first_text(entry, "title") or "(untitled)"
        link = ""
        for link_elem in children(entry, "link"):
            rel = link_elem.attrib.get("rel", "alternate")
            href = link_elem.attrib.get("href", "")
            if href and rel in {"alternate", ""}:
                link = href
                break
        link = link or first_text(entry, "link")
        entry_id = first_text(entry, "id")
        published_at = parse_datetime(first_text(entry, "published", "updated"))
        summary = first_text(entry, "summary", "content")
        final_id = stable_item_id(entry_id or link, title, published_at)
        items.append(
            MonitorItem(
                creator=creator_name,
                source_name=source_name,
                source_id=source_id,
                source_type="feed",
                title=title,
                url=link or entry_id or source.get("url", ""),
                published_at=published_at,
                fetched_at=fetched_at,
                summary=summary,
                tags=creator_tags + list(source.get("tags", [])),
                item_id=final_id,
            )
        )
    return items


def extract_html_title(text: str) -> str:
    for pattern in [
        r'(?is)<meta\s+property=["\']og:title["\']\s+content=["\']([^"\']+)["\']',
        r'(?is)<meta\s+name=["\']twitter:title["\']\s+content=["\']([^"\']+)["\']',
        r"(?is)<title[^>]*>(.*?)</title>",
    ]:
        match = re.search(pattern, text)
        if match:
            return clean_text(match.group(1), max_len=180)
    return "(page changed)"


def extract_canonical_url(text: str, fallback: str) -> str:
    match = re.search(r'(?is)<link\s+rel=["\']canonical["\']\s+href=["\']([^"\']+)["\']', text)
    if match:
        return html.unescape(match.group(1)).strip()
    return fallback


def content_fingerprint(text: str) -> str:
    text = re.sub(r"(?is)<(script|style|noscript).*?>.*?</\1>", " ", text)
    text = re.sub(r"(?is)<!--.*?-->", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", html.unescape(text)).strip().lower()
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def fetch_page_change(
    source: dict[str, Any],
    creator_name: str,
    creator_tags: list[str],
    state: dict[str, Any],
) -> list[MonitorItem]:
    url = source["url"]
    source_id = source.get("id") or source.get("name") or url
    source_name = source.get("name", source_id)
    body, final_url = fetch_url(url)
    text = body.decode("utf-8", errors="replace")
    fingerprint = content_fingerprint(text)
    old = state["page_hashes"].get(source_id)
    state["page_hashes"][source_id] = fingerprint

    if old in {None, fingerprint}:
        return []

    title = extract_html_title(text)
    canonical = extract_canonical_url(text, final_url)
    fetched_at = utc_now()
    return [
        MonitorItem(
            creator=creator_name,
            source_name=source_name,
            source_id=source_id,
            source_type="page",
            title=title,
            url=canonical,
            published_at=fetched_at,
            fetched_at=fetched_at,
            summary="Public page content changed since the last run.",
            tags=creator_tags + list(source.get("tags", [])),
            item_id=f"page-change:{fingerprint}",
        )
    ]


def fetch_x_api(
    source: dict[str, Any],
    creator_name: str,
    creator_tags: list[str],
) -> list[MonitorItem]:
    token_env = source.get("bearer_token_env", "X_BEARER_TOKEN")
    bearer = os.environ.get(token_env)
    if not bearer:
        raise RuntimeError(f"missing X API bearer token env var: {token_env}")

    handle = source["handle"].lstrip("@")
    headers = {"Authorization": f"Bearer {bearer}"}
    user_url = f"https://api.x.com/2/users/by/username/{urllib.parse.quote(handle)}"
    body, _ = fetch_url(user_url, headers=headers)
    user_data = json.loads(body.decode("utf-8"))
    user_id = user_data.get("data", {}).get("id")
    if not user_id:
        raise RuntimeError(f"X API could not resolve @{handle}")

    params = urllib.parse.urlencode(
        {
            "max_results": str(source.get("max_results", 20)),
            "tweet.fields": "created_at,entities,referenced_tweets",
            "exclude": "replies",
        }
    )
    tweets_url = f"https://api.x.com/2/users/{user_id}/tweets?{params}"
    body, _ = fetch_url(tweets_url, headers=headers)
    tweets = json.loads(body.decode("utf-8")).get("data", [])

    fetched_at = utc_now()
    source_id = source.get("id") or f"x:{handle}"
    source_name = source.get("name", f"X @{handle}")
    items: list[MonitorItem] = []
    for tweet in tweets:
        tweet_id = tweet["id"]
        text = clean_text(tweet.get("text", ""), max_len=500)
        url = f"https://x.com/{handle}/status/{tweet_id}"
        items.append(
            MonitorItem(
                creator=creator_name,
                source_name=source_name,
                source_id=source_id,
                source_type="x_api",
                title=text[:120] or f"Post {tweet_id}",
                url=url,
                published_at=parse_datetime(tweet.get("created_at", "")),
                fetched_at=fetched_at,
                summary=text,
                tags=creator_tags + list(source.get("tags", [])),
                item_id=tweet_id,
            )
        )
    return items


def _is_rate_limited(exc: Exception) -> bool:
    """Return True if the exception indicates a rate-limit / temporary server error."""
    if isinstance(exc, urllib.error.HTTPError):
        return exc.code in {429, 402, 502, 503}
    if isinstance(exc, OSError):
        msg = str(exc).lower()
        return any(kw in msg for kw in ("429", "rate", "limit", "too many"))
    return False


def _fetch_single(
    source_type: str,
    source: dict[str, Any],
    creator_name: str,
    creator_tags: list[str],
    state: dict[str, Any],
) -> list[MonitorItem]:
    if source_type in {"feed", "rss", "atom", "youtube"}:
        url = source["url"]
        body, _ = fetch_url(url)
        return parse_feed(body, source, creator_name, creator_tags)
    if source_type == "page":
        return fetch_page_change(source, creator_name, creator_tags, state)
    if source_type == "x_api":
        return fetch_x_api(source, creator_name, creator_tags)
    raise ValueError(f"unsupported source type: {source_type}")


def fetch_source(
    source: dict[str, Any],
    creator_name: str,
    creator_tags: list[str],
    state: dict[str, Any],
) -> list[MonitorItem]:
    source_type = source.get("type", "feed")
    try:
        return _fetch_single(source_type, source, creator_name, creator_tags, state)
    except (OSError, urllib.error.URLError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        fallback = source.get("fallback")
        if fallback and _is_rate_limited(exc):
            fb_type = fallback.get("type", "feed")
            fb_source = dict(source)
            fb_source.update(fallback)
            fb_source["type"] = fb_type
            fb_source["name"] = source.get("name", "") + " (fallback)"
            return _fetch_single(fb_type, fb_source, creator_name, creator_tags, state)
        raise


def should_include(
    item: MonitorItem,
    state: dict[str, Any],
    settings: dict[str, Any],
    keywords: list[str],
    init_seen: bool,
) -> bool:
    key = item_key(item.source_id, item.item_id)
    now = utc_now()
    seen = state["seen"].get(key)

    state["seen"][key] = {
        "creator": item.creator,
        "source": item.source_name,
        "title": item.title,
        "url": item.url,
        "first_seen": seen.get("first_seen") if isinstance(seen, dict) else now.isoformat(),
        "last_seen": now.isoformat(),
    }

    full_text = f"{item.title} {item.summary} {' '.join(item.tags)}"
    item.matched_keywords = match_keywords(full_text, keywords)

    if init_seen:
        return False

    if seen:
        return False

    include_without_keywords = bool(settings.get("include_items_without_keywords", True))
    if keywords and not include_without_keywords and not item.matched_keywords:
        return False

    lookback_hours = float(settings.get("lookback_hours", 48))
    if item.published_at:
        age = now - item.published_at
        if age > dt.timedelta(hours=lookback_hours):
            return False

    return True


def prune_state(state: dict[str, Any], retention_days: int) -> None:
    cutoff = utc_now() - dt.timedelta(days=retention_days)
    keep: dict[str, Any] = {}
    for key, value in state.get("seen", {}).items():
        try:
            last_seen = parse_datetime(value.get("last_seen", ""))
        except AttributeError:
            last_seen = None
        if last_seen is None or last_seen >= cutoff:
            keep[key] = value
    state["seen"] = keep


def format_dt(value: dt.datetime | None) -> str:
    if not value:
        return "unknown time"
    return value.astimezone(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def markdown_link(text: str, url: str) -> str:
    text = text.replace("[", "\\[").replace("]", "\\]")
    return f"[{text}]({url})" if url else text


def build_report(
    items: list[MonitorItem],
    warnings: list[str],
    config: dict[str, Any],
    generated_at: dt.datetime,
) -> str:
    settings = config.get("settings", {})
    title_en = settings.get("report_title", "Tech Creator Daily Monitor")
    title_cn = "科技博主日报"
    title = f"{title_cn} / {title_en}"

    total_active_creators = len(config.get("creators", []))
    total_sources = sum(len(c.get("sources", [])) for c in config.get("creators", []))
    all_keywords = list(settings.get("keywords", []))

    lines: list[str] = [
        f"# {title}",
        "",
        f"- Generated / 生成时间: {format_dt(generated_at)}",
        f"- New items / 新增条目: {len(items)}",
        "",
    ]

    # ─── Chinese Summary ───
    lines.extend(["## 中文摘要", ""])
    if not items:
        lines.append("本轮监控未发现新的关键词匹配条目。")
        lines.append("")
    else:
        keyword_items = [item for item in items if item.matched_keywords]
        lines.append(f"本轮新增 **{len(items)}** 条，其中 **{len(keyword_items)}** 条触发关键词匹配。")
        lines.append("")

        # Per-creator summary
        creator_counts: dict[str, int] = {}
        for item in items:
            creator_counts[item.creator] = creator_counts.get(item.creator, 0) + 1
        lines.append("各博主新增分布：")
        for creator, count in sorted(creator_counts.items(), key=lambda x: -x[1]):
            lines.append(f"- {creator}: {count} 条")
        lines.append("")

        # Top keywords
        kw_counter: dict[str, int] = {}
        for item in keyword_items:
            for kw in item.matched_keywords:
                kw_counter[kw] = kw_counter.get(kw, 0) + 1
        top_kw = sorted(kw_counter.items(), key=lambda x: -x[1])[:8]
        if top_kw:
            lines.append("高频关键词：")
            for kw, cnt in top_kw:
                lines.append(f"- `{kw}`: {cnt} 次")
            lines.append("")

        # Source types
        source_types: dict[str, int] = {}
        for item in items:
            st = item.source_type or "unknown"
            source_types[st] = source_types.get(st, 0) + 1
        lines.append("来源类型分布：")
        for st, cnt in sorted(source_types.items(), key=lambda x: -x[1]):
            lines.append(f"- {st}: {cnt}")
        lines.append("")

    # ─── English Summary ───
    lines.extend(["## English Summary", ""])
    if not items:
        lines.append("No new keyword-matched items detected this run.")
        lines.append("")
    else:
        kw_it = [item for item in items if item.matched_keywords]
        lines.append(f"{len(items)} new item(s) detected, {len(kw_it)} with keyword matches.")
        lines.append(f"Monitoring {total_active_creators} creators via {total_sources} sources across {len(all_keywords)} keywords.")
        lines.append("")

    # ─── Warnings ───
    if warnings:
        lines.extend(["## Warnings", ""])
        for warning in warnings:
            lines.append(f"- {warning}")
        lines.append("")

    if not items:
        lines.extend(["## No New Public Items", "", "No unseen items matched this run.", ""])
        lines.append("---")
        return "\n".join(lines)

    # ─── Keyword Signals ───
    keyword_items = [item for item in items if item.matched_keywords]
    if keyword_items:
        lines.extend(["## Keyword Signals / 关键词信号", ""])
        for item in sorted(keyword_items, key=lambda x: x.published_at or x.fetched_at, reverse=True):
            matched = ", ".join(item.matched_keywords)
            lines.append(
                f"- **{item.creator}** / {item.source_name}: "
                f"{markdown_link(item.title, item.url)} "
                f"`{matched}`"
            )
        lines.append("")

    # ─── New Items ───
    grouped: dict[str, list[MonitorItem]] = {}
    for item in items:
        grouped.setdefault(item.creator, []).append(item)

    lines.extend(["## New Items / 全部条目", ""])
    for creator in sorted(grouped):
        lines.append(f"### {creator}")
        for item in sorted(grouped[creator], key=lambda x: x.published_at or x.fetched_at, reverse=True):
            lines.append(f"- {markdown_link(item.title, item.url)}")
            lines.append(f"  - Source: {item.source_name} / {item.source_type}")
            lines.append(f"  - Time: {format_dt(item.published_at)}")
            if item.matched_keywords:
                lines.append(f"  - Keywords: {', '.join(item.matched_keywords)}")
            if item.summary:
                lines.append(f"  - Summary: {item.summary}")
        lines.append("")

    # ─── Footer separator for yesterday section ───
    lines.append("---")
    return "\n".join(lines)


def save_as_docx(text: str, path: Path) -> None:
    """Convert Markdown-like report text to a .docx file."""

    doc = Document()
    # Set default font
    style = doc.styles["Normal"]
    font = style.font
    font.name = "Calibri"
    font.size = Pt(11)

    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("# ") and not stripped.startswith("## "):
            doc.add_heading(stripped[2:], level=1)
        elif stripped.startswith("## "):
            doc.add_heading(stripped[3:], level=2)
        elif stripped.startswith("### "):
            doc.add_heading(stripped[4:], level=3)
        elif stripped.startswith("- "):
            doc.add_paragraph(stripped[2:], style="List Bullet")
        elif stripped.startswith("---"):
            doc.add_paragraph("─" * 50)
        else:
            doc.add_paragraph(stripped)

    doc.save(str(path))


def send_email(report: str, config: dict[str, Any], report_path: Path) -> None:
    delivery = config.get("delivery", {})
    email_cfg = delivery.get("email", {})
    if not email_cfg.get("enabled", False):
        return

    host = email_cfg["smtp_host"]
    port = int(email_cfg.get("smtp_port", 587))
    username_env_key = email_cfg.get("username_env", "SMTP_USERNAME")
    username = os.environ.get(username_env_key, "")
    password = os.environ.get(email_cfg.get("password_env", "SMTP_PASSWORD"), "")

    sender = email_cfg["from"]
    if sender == username_env_key:
        sender = username

    recipients = email_cfg["to"]
    if isinstance(recipients, str):
        recipients = [recipients]
    recipients = [username if r == username_env_key else r for r in recipients]

    msg = EmailMessage()
    subject = email_cfg.get("subject", "科技博主日报 / Tech Creator Daily Monitor")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg.add_attachment(
        report_path.read_bytes(),
        maintype="application",
        subtype="vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=report_path.name,
    )

    with smtplib.SMTP(host, port, timeout=30) as smtp:
        smtp.starttls()
        if username or password:
            smtp.login(username, password)
        smtp.send_message(msg)


def run(config_path: Path, init_seen: bool = False) -> Path:
    config = read_config(config_path)
    settings = config.get("settings", {})
    base_dir = config_path.parent
    report_dir = base_dir / settings.get("report_dir", "reports")
    state_dir = base_dir / settings.get("state_dir", "state")
    ensure_dirs(report_dir, state_dir)

    state_path = state_dir / "seen.json"
    state = load_state(state_path)
    keywords = list(settings.get("keywords", []))
    max_items_per_source = int(settings.get("max_items_per_source", 30))
    pause_seconds = float(settings.get("pause_seconds_between_sources", 0.5))

    new_items: list[MonitorItem] = []
    warnings: list[str] = []
    creators = config.get("creators", [])

    for creator in creators:
        creator_name = creator.get("name", "(unnamed creator)")
        creator_tags = list(creator.get("tags", []))
        for source in creator.get("sources", []):
            source_name = source.get("name", source.get("url", source.get("handle", "source")))
            try:
                items = fetch_source(source, creator_name, creator_tags, state)
                items = items[:max_items_per_source]
                for item in items:
                    if should_include(item, state, settings, keywords, init_seen):
                        new_items.append(item)
            except (OSError, urllib.error.URLError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
                warnings.append(f"{creator_name} / {source_name}: {exc}")
            time.sleep(pause_seconds)

    prune_state(state, int(settings.get("state_retention_days", 180)))
    save_state(state_path, state)

    generated_at = utc_now()
    date_stamp = generated_at.astimezone().strftime("%Y-%m-%d")
    report_path = report_dir / f"科技博主-{date_stamp}.docx"
    report = build_report(new_items, warnings, config, generated_at)

    # Append previous day's report
    prev_date = (generated_at.astimezone() - dt.timedelta(days=1)).strftime("%Y-%m-%d")
    prev_path_docx = report_dir / f"科技博主-{prev_date}.docx"
    prev_path_md = report_dir / f"科技博主-{prev_date}.md"
    if prev_path_docx.exists():
        prev_content = prev_path_docx.read_bytes()
        # .docx from previous day: extract text via Document
        try:
            prev_doc = Document(str(prev_path_docx))
            prev_lines = [p.text for p in prev_doc.paragraphs]
            prev_text = "\n".join(prev_lines)
        except Exception:
            prev_text = ""
        report += "\n\n---\n\n## 昨日回顾\n\n" + prev_text
    elif prev_path_md.exists():
        prev_content = prev_path_md.read_text(encoding="utf-8")
        report += "\n\n---\n\n## 昨日回顾\n\n" + prev_content

    save_as_docx(report, report_path)
    send_email(report, config, report_path)
    return report_path


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Monitor public creator feeds/pages/APIs and write a daily Markdown digest."
    )
    parser.add_argument(
        "--config",
        default=DEFAULT_CONFIG,
        help=f"Config file path. Default: {DEFAULT_CONFIG}",
    )
    parser.add_argument(
        "--init-seen",
        action="store_true",
        help="Record current items as already seen without reporting them.",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    config_path = Path(args.config).resolve()
    if not config_path.exists():
        print(f"Config not found: {config_path}", file=sys.stderr)
        return 2

    try:
        report_path = run(config_path, init_seen=args.init_seen)
    except Exception as exc:  # Keep scheduled task failures visible in logs.
        print(f"{APP_NAME} failed: {exc}", file=sys.stderr)
        return 1

    print(f"Report written: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
