#!/usr/bin/env python3
"""Verify every internal href/src on the generated site resolves to a real file."""
import re
import urllib.parse
from collections import Counter
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path("/Users/evanroberts/github/SamauraiSupply.com")
bad = Counter()
bad_examples = {}
n_pages = n_links = 0

def resolves(href):
    path = urllib.parse.unquote(href.split("#")[0].split("?")[0])
    if not path or path == "/":
        return True
    p = ROOT / path.lstrip("/")
    if path.endswith("/"):
        return (p / "index.html").is_file()
    return p.is_file() or (p / "index.html").is_file()

for f in ROOT.rglob("*.html"):
    if ".git" in f.parts:
        continue
    n_pages += 1
    soup = BeautifulSoup(f.read_text(encoding="utf-8", errors="replace"), "html.parser")
    for tag, attr in (("a", "href"), ("img", "src"), ("link", "href"), ("script", "src")):
        for t in soup.find_all(tag):
            v = t.get(attr)
            if not v or v.startswith(("http", "mailto:", "#", "data:")):
                continue
            n_links += 1
            if not v.startswith("/"):
                bad[f"RELATIVE:{v}"] += 1
                bad_examples.setdefault(f"RELATIVE:{v}", str(f.relative_to(ROOT)))
                continue
            if not resolves(v):
                bad[v] += 1
                bad_examples.setdefault(v, str(f.relative_to(ROOT)))

print(f"pages={n_pages} internal_refs={n_links} broken_targets={len(bad)}")
for target, count in bad.most_common(40):
    print(f"{count:5d}  {target}   e.g. in {bad_examples[target]}")
