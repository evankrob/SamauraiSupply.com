#!/usr/bin/env python3
"""Extract product catalog + content pages from the old Vendio store scrape."""
import json
import re
import sys
import urllib.parse
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path("/Users/evanroberts/github/SamauraiSupply.com")
OUT = Path(__file__).parent

# ---------- thumbnail map: product_id -> path ----------
thumbs = {}
for p in ROOT.glob("image_manager/attributes/image/*/*"):
    name = p.name
    if "humbnail" in name or "HUMBNAIL" in name:
        pid = name.split("_", 1)[0]
        thumbs.setdefault(pid, "/" + str(p.relative_to(ROOT)))

def file_exists(src: str) -> bool:
    src = src.strip()
    if not src.startswith("/"):
        return False
    path = ROOT / urllib.parse.unquote(src.lstrip("/"))
    return path.is_file()

def parse_product(path: Path):
    raw = path.read_bytes()
    soup = BeautifulSoup(raw, "html.parser", from_encoding="ISO-8859-1")
    rec = {"file": path.name}
    m = re.search(r"_(\d+)\.html$", path.name)
    rec["product_id"] = m.group(1) if m else None

    title = soup.title.get_text(strip=True) if soup.title else path.stem
    rec["title"] = title
    # name/sku from title "Name - SKU"
    if " - " in title:
        name, sku = title.rsplit(" - ", 1)
        rec["name"], rec["sku"] = name.strip(), sku.strip()
    else:
        rec["name"], rec["sku"] = title.strip(), ""

    # category breadcrumb
    cat = soup.find("a", href=re.compile(r"store-categories-"))
    if cat:
        rec["category_file"] = urllib.parse.unquote(cat["href"].lstrip("/"))
        rec["category_name"] = cat.get_text(strip=True)
    else:
        rec["category_file"] = None
        rec["category_name"] = None

    # brand: variant A: <font color=red>NAME</font></b><br><b>BRAND</b>; variant B: Brand: row
    brand = None
    ftag = soup.find("font", attrs={"color": re.compile("red", re.I)})
    if ftag:
        b = ftag.find_parent("b")
        if b:
            nb = b.find_next_sibling("b")
            if nb:
                brand = nb.get_text(strip=True)
    if not brand:
        bh = soup.find("td", class_="productheading", string=re.compile(r"Brand:"))
        if bh:
            bi = bh.find_next_sibling("td")
            if bi:
                brand = bi.get_text(strip=True)
    rec["brand"] = brand or ""

    # prices
    text = soup.get_text(" ")
    m = re.search(r"Your price:\s*\$?([\d,]+\.?\d*)", text)
    if not m:
        m = re.search(r"Price\s*\$?([\d,]+\.\d{2})", text)
    rec["price"] = m.group(1) if m else None

    # main image: first existing /image_manager/attributes img
    rec["image"] = None
    for img in soup.find_all("img", src=re.compile(r"/image_manager/attributes/")):
        src = img.get("src", "").strip()
        if file_exists(src):
            rec["image"] = src
            break
    rec["thumb"] = thumbs.get(rec["product_id"]) or rec["image"]

    # description: variant A blockquote, else variant B Description: cell
    desc = soup.find("blockquote")
    if not desc:
        dh = soup.find("td", class_="productheading", string=re.compile(r"Description:"))
        if dh:
            desc = dh.find_next_sibling("td")
    rec["desc_html"] = str(desc) if desc else ""
    return rec

products = []
failures = []
for path in sorted(ROOT.glob("store-products-*.html")):
    if "PHPSESSID" in path.name:
        continue
    try:
        products.append(parse_product(path))
    except Exception as e:  # noqa: BLE001
        failures.append((path.name, str(e)))

# ---------- content pages (slug dirs) ----------
def extract_dir_page(path: Path):
    raw = path.read_bytes()
    soup = BeautifulSoup(raw, "html.parser", from_encoding="ISO-8859-1")
    rec = {"dir": str(path.parent.relative_to(ROOT))}
    rec["title"] = soup.title.get_text(strip=True) if soup.title else ""
    md = soup.find("meta", attrs={"name": "description"})
    rec["meta_desc"] = md.get("content", "").strip() if md else ""
    # product links in order
    seen, links = set(), []
    for a in soup.find_all("a", href=re.compile(r"store-products-")):
        href = urllib.parse.unquote(a["href"])
        href = re.sub(r"^https?://(www\.)?samuraisupply\.com", "", href).lstrip("/")
        if href not in seen:
            seen.add(href)
            links.append(href)
    rec["product_links"] = links
    # main content: the white td after logo with the most text
    best, best_len = None, 0
    for td in soup.find_all("td"):
        style = (td.get("style") or "") + (td.get("bgcolor") or "")
        if "FFFFFF" not in style and "ffffff" not in style:
            continue
        if td.find("img", src=re.compile("company_logo")):
            continue
        n = len(td.get_text(strip=True))
        if n > best_len:
            best, best_len = td, n
    rec["content_html"] = str(best) if best else ""
    return rec

pages = []
for idx in sorted(ROOT.glob("*/index.html")):
    d = idx.parent.name
    if d.startswith("?") or d in ("admin", "themes", "store", "image_manager", "my_files"):
        continue
    try:
        pages.append(extract_dir_page(idx))
    except Exception as e:  # noqa: BLE001
        failures.append((str(idx), str(e)))

(OUT / "catalog.json").write_text(json.dumps(products, indent=1))
(OUT / "pages.json").write_text(json.dumps(pages, indent=1))

# ---------- report ----------
n_img = sum(1 for p in products if p["image"])
n_cat = sum(1 for p in products if p["category_file"])
n_desc = sum(1 for p in products if len(p["desc_html"]) > 50)
n_brand = sum(1 for p in products if p["brand"])
ids = {}
for p in products:
    ids.setdefault(p["product_id"], []).append(p["file"])
dupes = {k: v for k, v in ids.items() if len(v) > 1}
print(f"products: {len(products)}  failures: {len(failures)}")
print(f"with image: {n_img}  with category: {n_cat}  with desc: {n_desc}  with brand: {n_brand}")
print(f"duplicate product_ids: {len(dupes)}")
print(f"dir pages: {len(pages)}  with products: {sum(1 for p in pages if p['product_links'])}")
for f in failures[:10]:
    print("FAIL", f)
no_cat = [p["file"] for p in products if not p["category_file"]][:10]
print("no category sample:", no_cat)
no_img = [p["file"] for p in products if not p["image"]][:10]
print("no image sample:", no_img)
