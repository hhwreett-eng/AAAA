#!/usr/bin/env python3
"""Build a recent multi-day digest without using the daily de-duplication state."""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import monitor


THEMES = {
    "Nvidia/GPU": ["NVIDIA", "NVDA", "Blackwell", "Rubin", "CUDA", "GPU"],
    "Cloud/CSP/Capex": [
        "hyperscaler",
        "hyperscalers",
        "CSP",
        "cloud",
        "AWS",
        "Azure",
        "Google Cloud",
        "Oracle Cloud",
        "capex",
        "data center",
        "datacenter",
    ],
    "AI Infrastructure": ["AI infrastructure", "inference", "training", "CoreWeave", "neocloud", "networking"],
    "Semiconductor Chain": ["AMD", "TSMC", "ASML", "Broadcom", "AVGO", "Marvell", "MRVL", "HBM", "memory"],
    "Software/SaaS": ["SaaS", "software", "enterprise", "agentic", "Cloudflare", "Snowflake", "Databricks"],
}


def source_label(source: dict[str, Any]) -> str:
    return source.get("name") or source.get("url") or source.get("handle") or "(source)"


def item_text(item: monitor.MonitorItem) -> str:
    return f"{item.title} {item.summary} {' '.join(item.tags)}"


def theme_hits(item: monitor.MonitorItem) -> list[str]:
    text = item_text(item).lower()
    hits = []
    for theme, keywords in THEMES.items():
        if any(keyword.lower() in text for keyword in keywords):
            hits.append(theme)
    return hits


def build_recent_digest(config_path: Path, days: int, limit: int) -> Path:
    config = monitor.read_config(config_path)
    settings = config.get("settings", {})
    report_dir = config_path.parent / settings.get("report_dir", "reports")
    monitor.ensure_dirs(report_dir)

    cutoff = monitor.utc_now() - dt.timedelta(days=days)
    state = {"seen": {}, "page_hashes": {}}
    keywords = list(settings.get("keywords", []))
    items: list[monitor.MonitorItem] = []
    warnings: list[str] = []
    skipped_pages: list[str] = []
    feed_sources: list[tuple[str, str, str]] = []

    for creator in config.get("creators", []):
        creator_name = creator.get("name", "(unnamed creator)")
        creator_tags = list(creator.get("tags", []))
        for source in creator.get("sources", []):
            source_type = source.get("type", "feed")
            name = source_label(source)
            url = source.get("url", "")
            if source_type == "page":
                skipped_pages.append(f"{creator_name} / {name}")
                continue
            if source_type in {"feed", "rss", "atom", "youtube"}:
                feed_sources.append((creator_name, name, url))
            try:
                fetched = monitor.fetch_source(source, creator_name, creator_tags, state)
                for item in fetched:
                    published = item.published_at or item.fetched_at
                    if published >= cutoff:
                        item.matched_keywords = monitor.match_keywords(item_text(item), keywords)
                        items.append(item)
            except Exception as exc:
                warnings.append(f"{creator_name} / {name}: {exc}")

    items.sort(key=lambda item: item.published_at or item.fetched_at, reverse=True)
    if limit > 0:
        items = items[:limit]

    theme_counter: Counter[str] = Counter()
    creator_counter: Counter[str] = Counter()
    keyword_counter: Counter[str] = Counter()
    source_counter: Counter[str] = Counter()
    for item in items:
        creator_counter[item.creator] += 1
        source_counter[item.source_name] += 1
        keyword_counter.update(item.matched_keywords)
        theme_counter.update(theme_hits(item))

    generated_at = monitor.utc_now()
    report_path = report_dir / f"recent-{days}d-{generated_at.astimezone(dt.timezone.utc).strftime('%Y-%m-%d')}.md"
    lines: list[str] = [
        f"# Recent {days}-Day Tech Stock Creator Digest",
        "",
        f"- Generated: {monitor.format_dt(generated_at)}",
        f"- Window start: {monitor.format_dt(cutoff)}",
        f"- Public feed/API sources checked: {len(feed_sources)}",
        f"- Page-change sources skipped for dated digest: {len(skipped_pages)}",
        f"- Items in window: {len(items)}",
        "",
        "## Source Interfaces",
        "",
    ]
    for creator_name, name, url in feed_sources:
        lines.append(f"- **{creator_name}** / {name}: {url}")
    lines.append("")

    if warnings:
        lines.extend(["## Fetch Warnings", ""])
        for warning in warnings:
            lines.append(f"- {warning}")
        lines.append("")

    lines.extend(["## Signal Analysis", ""])
    if items:
        lines.append("### Theme Counts")
        for theme, count in theme_counter.most_common():
            lines.append(f"- {theme}: {count}")
        lines.append("")
        lines.append("### Most Active Creators")
        for creator, count in creator_counter.most_common(10):
            lines.append(f"- {creator}: {count}")
        lines.append("")
        lines.append("### Top Keyword Hits")
        for keyword, count in keyword_counter.most_common(20):
            lines.append(f"- {keyword}: {count}")
        lines.append("")
    else:
        lines.extend(["No items were found in this window.", ""])

    grouped: dict[str, list[monitor.MonitorItem]] = defaultdict(list)
    for item in items:
        day = (item.published_at or item.fetched_at).astimezone(dt.timezone.utc).strftime("%Y-%m-%d")
        grouped[day].append(item)

    lines.extend(["## Items", ""])
    for day in sorted(grouped, reverse=True):
        lines.append(f"### {day}")
        for item in grouped[day]:
            themes = ", ".join(theme_hits(item)) or "Unclassified"
            keywords_text = ", ".join(item.matched_keywords) or "none"
            lines.append(f"- **{item.creator}** / {item.source_name}: {monitor.markdown_link(item.title, item.url)}")
            lines.append(f"  - Time: {monitor.format_dt(item.published_at)}")
            lines.append(f"  - Themes: {themes}")
            lines.append(f"  - Keywords: {keywords_text}")
            if item.summary:
                lines.append(f"  - Summary: {item.summary}")
        lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a recent multi-day public-source digest.")
    parser.add_argument("--config", default=monitor.DEFAULT_CONFIG)
    parser.add_argument("--days", type=int, default=5)
    parser.add_argument("--limit", type=int, default=200)
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    path = build_recent_digest(Path(args.config).resolve(), args.days, args.limit)
    print(f"Recent digest written: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
