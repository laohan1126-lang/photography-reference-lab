#!/usr/bin/env python3
"""Check source URLs in references.yaml for availability and redirects.
Checks all references by default, or limits with --limit <N>.
"""

import sys
import argparse
import urllib.request
import ssl
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
DATA_YAML = ROOT / "data" / "references.yaml"

def check_sources(timeout=8, limit=None):
    if not DATA_YAML.exists():
        print(f"Error: {DATA_YAML} not found.")
        sys.exit(1)

    with open(DATA_YAML, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if limit is not None and limit > 0:
        check_list = data[:limit]
    else:
        check_list = data

    ctx = ssl._create_unverified_context()
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    results = []
    print(f"Checking sources for {len(check_list)} references (timeout={timeout}s)...")
    
    for idx, ref in enumerate(check_list):
        ref_id = ref.get("id")
        url = ref.get("source", {}).get("url")
        if not url:
            results.append((ref_id, "EMPTY", "Missing URL"))
            continue

        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, context=ctx, timeout=timeout) as res:
                code = res.status
                final_url = res.url
                status = "OK" if code == 200 else f"HTTP_{code}"
                if final_url != url:
                    status += " (REDIRECTED)"
                results.append((ref_id, status, url))
        except urllib.error.HTTPError as e:
            results.append((ref_id, f"HTTP_{e.code}", url))
        except Exception as e:
            results.append((ref_id, "FAILED", str(e)[:50]))

    print("=" * 80)
    print(f"{'ID':<15} | {'STATUS':<20} | {'URL / REASON'}")
    print("-" * 80)
    for ref_id, status, u in results:
        print(f"{ref_id:<15} | {status:<20} | {u[:70]}")
    print("=" * 80)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check references.yaml URLs")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of references to check")
    parser.add_argument("--timeout", type=int, default=8, help="Request timeout in seconds")
    args = parser.parse_args()
    check_sources(timeout=args.timeout, limit=args.limit)
