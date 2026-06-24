#!/usr/bin/env python3
"""
OMEGA RESTART TRACKER
Parses guardian.log for RESTART events, counts per-process,
flags processes with high restart counts (instability signal).

Supports a rolling 24-hour window so a problem fixed yesterday
doesn't keep showing as "UNSTABLE" forever. Full history stays in
guardian.log; archive_and_reset() snapshots the day's totals to
omega_restart_archive.jsonl and rotates the log for a clean cycle.
"""
import re
import os
import json
from collections import Counter
from datetime import datetime, timedelta

LOG_PATH = os.path.expanduser("~/omega_runtime/logs/guardian.log")
ARCHIVE_PATH = os.path.expanduser("~/omega_runtime/logs/omega_restart_archive.jsonl")

TS_FORMATS = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f"]


def _parse_ts(timestamp_str):
    for fmt in TS_FORMATS:
        try:
            return datetime.strptime(timestamp_str.strip(), fmt)
        except ValueError:
            continue
    return None


def parse_restarts(since: datetime = None):
    if not os.path.exists(LOG_PATH):
        return Counter(), []

    pattern = re.compile(r"\[(.*?)\]\s*RESTART:\s*(.+)")
    counts = Counter()
    recent = []

    with open(LOG_PATH) as f:
        for line in f:
            m = pattern.search(line)
            if not m:
                continue
            timestamp_str, process = m.group(1), m.group(2).strip()

            if since is not None:
                ts = _parse_ts(timestamp_str)
                if ts is not None and ts < since:
                    continue

            counts[process] += 1
            recent.append((timestamp_str, process))

    return counts, recent


def report(window_hours: int = 24):
    since = None
    label = "ALL-TIME"
    if window_hours is not None:
        since = datetime.now() - timedelta(hours=window_hours)
        label = f"LAST {window_hours}H"

    counts, recent = parse_restarts(since=since)

    print("=" * 56)
    print(f"  OMEGA RESTART TRACKER  ({label})")
    print("=" * 56)

    if not counts:
        print("  No restart events in this window — system stable.")
        print("=" * 56)
        return counts

    for process, count in sorted(counts.items(), key=lambda x: -x[1]):
        flag = ""
        if count >= 10:
            flag = "  WARNING: UNSTABLE"
        elif count >= 5:
            flag = "  watch"
        print(f"  {process:30} {count:4} restarts{flag}")

    print("=" * 56)
    print(f"  Total restart events in window: {sum(counts.values())}")
    print("=" * 56)

    return counts


def archive_and_reset():
    since = datetime.now() - timedelta(hours=24)
    counts, _ = parse_restarts(since=since)

    entry = {
        "archived_at": datetime.now().isoformat(timespec="seconds"),
        "window_hours": 24,
        "counts": dict(counts),
        "total": sum(counts.values()),
    }

    os.makedirs(os.path.dirname(ARCHIVE_PATH), exist_ok=True)
    with open(ARCHIVE_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")

    rotated = None
    if os.path.exists(LOG_PATH):
        rotated = LOG_PATH + "." + datetime.now().strftime("%Y%m%d") + ".bak"
        os.replace(LOG_PATH, rotated)
        open(LOG_PATH, "a").close()

    print(f"[{datetime.now().isoformat(timespec='seconds')}] "
          f"Archived {entry['total']} restart events from last 24h "
          f"-> {ARCHIVE_PATH}")
    print(f"Rotated guardian.log -> {rotated if rotated else '(none, log was empty)'}")

    return entry


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "archive":
        archive_and_reset()
    elif len(sys.argv) > 1 and sys.argv[1] == "all":
        report(window_hours=None)
    else:
        report(window_hours=24)
