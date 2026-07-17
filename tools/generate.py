#!/usr/bin/env python3
"""Regenerate SamuraiSupply.com as a fast, clean Amazon-affiliate archive site."""
import html as html_mod
import json
import re
import urllib.parse
from pathlib import Path

from bs4 import BeautifulSoup, Comment
from PIL import Image

ROOT = Path("/Users/evanroberts/github/SamauraiSupply.com")
HERE = Path(__file__).parent
BASE = "https://samuraisupply.com"
TAG = "ralefive-20"

catalog = json.loads((HERE / "catalog.json").read_text())
pages = json.loads((HERE / "pages.json").read_text())

# ------------------------------------------------------------------ data prep
def norm_cat(f):
    return f.split("?")[0] if f else None

for p in catalog:
    p["category_file"] = norm_cat(p["category_file"])
    if p.get("brand", "").strip().lower() == p.get("sku", "").strip().lower():
        p["brand"] = ""

by_id = {}
for p in sorted(catalog, key=lambda x: x["file"]):
    by_id.setdefault(p["product_id"], []).append(p)
primary_of = {}          # product_id -> primary record
for pid, recs in by_id.items():
    # prefer record with an image and longest description
    primary = sorted(recs, key=lambda r: (bool(r["image"]), len(r["desc_html"]), -len(r["file"])), reverse=True)[0]
    primary_of[pid] = primary

cats = {}                # category_file -> {"name":..., "products":[primary recs]}
for pid, rec in primary_of.items():
    cf = rec["category_file"]
    c = cats.setdefault(cf, {"name": rec["category_name"], "products": []})
    c["products"].append(rec)
for c in cats.values():
    c["products"].sort(key=lambda r: r["name"].lower())

SLUG_TO_CAT = {
    "assemble_yourself_katana_swords": "store-categories-Assemble-Yourself-Katana-Swords_3553436.html",
    "automotive": "store-categories-Automotive_4277664.html",
    "bokken_samurai_swords": "store-categories-Bokken-Samurai-Swords_3556081.html",
    "bushido_samurai_swords": "store-categories-Bushido-Samurai-Swords_3553589.html",
    "cold_steel_samurai_swords": "store-categories-Cold-Steel-Samurai-Swords_3553591.html",
    "decorative_samurai_swords": "store-categories-Decorative-Swords_3556061.html",
    "handmade_samurai_swords": "store-categories-Handmade-Samurai-Swords_3556297.html",
    "hanwei_paul_chen_samurai_swords": "store-categories-Hanwei-Paul-Chen-Swords_3556313.html",
    "hanwei-shuihu-tachi": "store-categories-Hanwei-Shuihu-Tachi_4275006.html",
    "japanese_art": "store-categories-Japanese-Art_4123993.html",
    "katsumoto_samurai_swords": "store-categories-Katsumoto-Samurai-Swords_3556575.html",
    "kawashima_samurai_swords": "store-categories-Kawashima-Samurai-Swords_3557002.html",
    "kendo_equipment": "store-categories-Kendo-Equipment-and-Supplies_4088340.html",
    "masahiro_samurai_swords": "store-categories-Masahiro-Samurai-Swords_3556557.html",
    "musashi_samurai_swords": "store-categories-Musashi-Samurai-Swords_3556559.html",
    "rittersteel_samurai_swords": "store-categories-Rittersteel-Samurai-Swords_3580052.html",
    "ryumon_samurai_swords": "store-categories-Ryumon-Samurai-Swords_3557003.html",
    "samurai_katanas": "store-categories-Samurai-Katanas_4291409.html",
    "samurai_sword_cutting_mats_and_stands": "store-categories-Samurai-Sword-Cutting-Mats-and-Stands_3585567.html",
    "samurai_sword_maintenance_kits": "store-categories-Samurai-Sword-Maintenance-Kits_3585563.html",
    "samurai_sword_stands_and_accessories": "store-categories-Samurai-Sword-Accessories_3881749.html",
    "samurai_sword_tsubas": "store-categories-Samurai-Sword-Tsuba_3585561.html",
    "sword_bags": "store-categories-Sword-Bags_3685808.html",
    "ten_ryu_samurai_swords": "store-categories-Ten-Ryu-Samurai-Swords_4210136.html",
    "thaitsuki_samurai_sword": "store-categories-Thaitsuki-Samurai-Sword_3580115.html",
    "throwing-weapons": "store-categories-Throwing-Weapons_3838151.html",
    "tora_tsume_samurai_swords": "store-categories-Tora-Tsume-Samurai-Swords-(TM)_4202155.html",
}
SLUG_TITLES = {
    "assemble_yourself_katana_swords": "Assemble-Yourself Katana Swords",
    "automotive": "Radiator Hose Filters",
    "bokken_samurai_swords": "Bokken & Training Swords",
    "bushido_samurai_swords": "Bushido Samurai Swords",
    "cold_steel_samurai_swords": "Cold Steel Swords",
    "decorative_samurai_swords": "Decorative & Movie Swords",
    "handmade_samurai_swords": "Handmade Samurai Swords",
    "hanwei_paul_chen_samurai_swords": "Hanwei Paul Chen Swords",
    "hanwei-shuihu-tachi": "Hanwei Shuihu Tachi",
    "japanese_art": "Japanese Art",
    "katsumoto_samurai_swords": "Katsumoto Samurai Swords",
    "kawashima_samurai_swords": "Kawashima Samurai Swords",
    "kendo_equipment": "Kendo Equipment",
    "masahiro_samurai_swords": "Masahiro Samurai Swords",
    "musashi_samurai_swords": "Musashi & Musha Katana Swords",
    "rittersteel_samurai_swords": "Rittersteel Samurai Swords",
    "ryumon_samurai_swords": "Ryumon Samurai Swords",
    "samurai_katanas": "Samurai Katanas",
    "samurai_sword_cutting_mats_and_stands": "Tameshigiri Mats & Stands",
    "samurai_sword_maintenance_kits": "Sword Maintenance Kits",
    "samurai_sword_stands_and_accessories": "Sword Stands & Accessories",
    "samurai_sword_tsubas": "Tsuba — Sword Guards",
    "sword_bags": "Sword Bags",
    "ten_ryu_samurai_swords": "Ten Ryu Samurai Swords",
    "thaitsuki_samurai_sword": "Thaitsuki Samurai Swords",
    "throwing-weapons": "Throwing Weapons",
    "tora_tsume_samurai_swords": "Tora Tsume Samurai Swords",
}
# category_file -> primary slug page
CAT_TO_SLUG = {}
for slug, cf in SLUG_TO_CAT.items():
    CAT_TO_SLUG.setdefault(cf, slug)

ARTICLES = [
    ("who_is_hpc", "Who Is Hanwei Paul Chen?", "The story behind the Hanwei forge and Paul Chen's swords."),
    ("finding_a_quality_samurai_sword", "Finding a Quality Samurai Sword", "What separates a wall-hanger from a functional blade."),
    ("advantages_of_replica_movie_swords", "Advantages of Replica Movie Swords", "Why replica and movie swords earn a place in a collection."),
    ("making_your_own_training_sword", "Making Your Own Training Sword", "A guide to building a bokken for practice."),
    ("bokken_swords_for_training", "Bokken Swords for Training", "Choosing the right wooden sword for martial arts practice."),
    ("sword_terminology", "Japanese Sword Terminology", "Kissaki to kashira — the vocabulary of the katana."),
    ("the_kogarasu_maru_style_blade", "The Kogarasu Maru Style Blade", "The unusual double-edged tachi of legend."),
    ("glorious_dragon_article", "Musashi Glorious Dragon Katana", "A close look at the Musashi Glorious Dragon."),
    ("musashi_elite_katana_article", "Musashi Elite Katana", "A close look at the Musashi Elite."),
    ("rose_blossom_katana_article", "Musashi Rose Blossom Katana", "A close look at the Musashi Rose Blossom."),
    ("ryumon_swords", "About Ryumon Swords", "The Ryumon forge and its hand-forged katana line."),
    ("sky_jiro_samurai_swords", "Sky Jiro Samurai Swords", "About the Sky Jiro line of samurai swords."),
    ("tj_samurai_swords", "TJ Samurai Swords", "About the TJ line of samurai swords."),
    ("hakama", "Hakama", "Traditional Japanese hakama for martial arts."),
    ("testimonials", "Testimonials", "Letters from customers of the original Samurai Supply shop."),
]
ARTICLE_SLUGS = {a[0] for a in ARTICLES}

REDIRECTS = {
    "exclusive_katana_swords": "/samurai_katanas/",
    "hanwei_paul_chen_samauri_swords": "/hanwei_paul_chen_samurai_swords/",
    "samurai_sword_accessories": "/samurai_sword_stands_and_accessories/",
    "ten_ryu_samurai_swords_page2": "/ten_ryu_samurai_swords/",
    "ten_ryu_samurai_swords_page3": "/ten_ryu_samurai_swords/",
    "new_arrivals": "/",
    "martial_arts_weapons": "/",
    "the_martial_artist": "/",
    "the_gathering_2012": "/sword_articles/",
    "km": "/",
    "thank_you": "/",
    "custom-orders": "/",
    "income-_opportunity": "/",
    "international_orders": "/",
    "store_policies": "/about_us/",
    "related_links": "/sword_articles/",
}

NAV_BRANDS = [
    ("Bushido", "/bushido_samurai_swords/"), ("Cold Steel", "/cold_steel_samurai_swords/"),
    ("Hanwei Paul Chen", "/hanwei_paul_chen_samurai_swords/"), ("Katsumoto", "/katsumoto_samurai_swords/"),
    ("Kawashima", "/kawashima_samurai_swords/"), ("Masahiro", "/masahiro_samurai_swords/"),
    ("Musashi", "/musashi_samurai_swords/"), ("Rittersteel", "/rittersteel_samurai_swords/"),
    ("Ryumon", "/ryumon_samurai_swords/"), ("Ten Ryu", "/ten_ryu_samurai_swords/"),
    ("Thaitsuki", "/thaitsuki_samurai_sword/"), ("Tora Tsume", "/tora_tsume_samurai_swords/"),
]
NAV_GEAR = [
    ("Samurai Katanas", "/samurai_katanas/"), ("Assemble-Yourself Katanas", "/assemble_yourself_katana_swords/"),
    ("Bokken & Training", "/bokken_samurai_swords/"), ("Decorative & Movie Swords", "/decorative_samurai_swords/"),
    ("Handmade Swords", "/handmade_samurai_swords/"), ("Kendo Equipment", "/kendo_equipment/"),
    ("Hakama", "/hakama/"), ("Tsuba", "/samurai_sword_tsubas/"),
    ("Tameshigiri Mats & Stands", "/samurai_sword_cutting_mats_and_stands/"),
    ("Maintenance Kits", "/samurai_sword_maintenance_kits/"), ("Sword Bags", "/sword_bags/"),
    ("Stands & Accessories", "/samurai_sword_stands_and_accessories/"), ("Japanese Art", "/japanese_art/"),
]

# ------------------------------------------------------------------ helpers
esc = html_mod.escape
_dim_cache = {}

def img_dims(src):
    if src in _dim_cache:
        return _dim_cache[src]
    try:
        with Image.open(ROOT / urllib.parse.unquote(src.lstrip("/"))) as im:
            _dim_cache[src] = im.size
    except Exception:  # noqa: BLE001
        _dim_cache[src] = None
    return _dim_cache[src]

def href_of(fname):
    return "/" + urllib.parse.quote(fname)

def amazon_url(query):
    query = re.sub(r"\([^)]*\)", " ", query)
    query = re.sub(r"\s+", " ", query).strip()
    return "https://www.amazon.com/s?" + urllib.parse.urlencode({"k": query, "tag": TAG})

def amazon_query(rec):
    name = rec["name"]
    brand = rec.get("brand") or ""
    if brand and brand.lower() not in name.lower():
        name = f"{brand} {name}"
    return name

JUNK_RE = re.compile(
    r"money.?back|satisfaction guarantee|discount|coupon|sign.?up|supply member|members by filling"
    r"|supplies last|we ship|international order|paypal|order now|store polic|sportkaratemuseum"
    r"|stands 100|stands behind|on sale for|regular price|peace of mind|take action and purchase"
    r"|free shipping|toll free|email us|fill out|click here to view|add to cart|call us"
    r"|purchase this|purchase the|order yours|immediate discount|at checkout|sizes available|@",
    re.I,
)
JUNK_LIGHT_RE = re.compile(
    r"order now|coupon|discount code|we ship|paypal|add to cart|sign.?up now|fill out the form", re.I
)

def _clean_soup(soup, junk_re):
    for t in soup(["script", "form", "input", "style", "iframe", "noscript", "select", "option", "meta", "link"]):
        t.decompose()
    for c in soup.find_all(string=lambda s: isinstance(s, Comment)):
        c.extract()
    # kill junk blocks before unwrapping structure
    for t in soup.find_all(["p", "li", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote"]):
        if junk_re.search(t.get_text(" ", strip=True) or ""):
            t.decompose()
    for t in soup.find_all("div"):
        txt = t.get_text(" ", strip=True) or ""
        if len(txt) < 600 and junk_re.search(txt) and not t.find(["table", "ul"]):
            t.decompose()
    # images: keep only ones that exist locally
    for img in soup.find_all("img"):
        src = (img.get("src") or "").strip()
        src = re.sub(r"^https?://(www\.)?samuraisupply\.com", "", src)
        if not src.startswith(("/image_manager", "/my_files")) or not img_dims(src):
            img.decompose()
            continue
        w, h = img_dims(src)
        img.attrs = {"src": src, "alt": img.get("alt") or "", "width": w, "height": h,
                     "loading": "lazy", "decoding": "async"}
    # links
    for a in soup.find_all("a"):
        href = (a.get("href") or "").strip()
        href = re.sub(r"^(https?://)?(www\.)?samuraisupply\.com", "", href)
        if href and not href.startswith(("/", "http", "mailto:", "javascript:", "#")):
            a.unwrap()
            continue
        if not href or href.startswith(("javascript:", "/store/", "mailto:")) or "addthis" in href or "PHPSESSID" in href:
            a.unwrap()
            continue
        if href.startswith("http"):
            a.attrs = {"href": href, "rel": "nofollow noopener", "target": "_blank"}
        else:
            a.attrs = {"href": urllib.parse.quote(urllib.parse.unquote(href), safe="/:%()&=?_")}
    # structural unwraps
    for tag in ("font", "span", "u", "center", "big", "small", "section", "article", "tbody"):
        for t in soup.find_all(tag):
            t.unwrap()
    for t in soup.find_all("b"):
        t.name = "strong"
    for t in soup.find_all("i"):
        t.name = "em"
    # strip presentational attributes
    keep = {"img": {"src", "alt", "width", "height", "loading", "decoding"},
            "a": {"href", "rel", "target"}}
    for t in soup.find_all(True):
        allowed = keep.get(t.name, set())
        t.attrs = {k: v for k, v in t.attrs.items() if k in allowed}
    # drop <br> runs and empties
    out = str(soup)
    out = re.sub(r"(?:\s*<br\s*/?>\s*){2,}", "<br>", out)
    soup = BeautifulSoup(out, "html.parser")
    for _ in range(3):
        for t in soup.find_all(["p", "div", "li", "ul", "strong", "em", "h1", "h2", "h3", "h4", "table", "tr", "td", "blockquote"]):
            if not t.get_text(strip=True) and not t.find("img"):
                t.decompose()
    return str(soup).replace("\xa0", " ")

def sanitize(desc_html, light=False):
    if not desc_html:
        return ""
    soup = BeautifulSoup(desc_html, "html.parser")
    root = soup.find(["blockquote", "td"])
    if root and root.name in ("blockquote", "td"):
        root.unwrap()
    return _clean_soup(soup, JUNK_LIGHT_RE if light else JUNK_RE)

# ------------------------------------------------------------------ templates
CSS = """/* Samurai Supply — single stylesheet */
:root{--paper:#f3ebda;--paper2:#ece1c8;--card:#faf5e9;--ink:#221c14;--ink2:#6b5f4d;
--crimson:#9e1b1b;--crimson-d:#771111;--gold:#a8802e;--line:#d9c9a6;--dark:#191410;--dark2:#241d16}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--paper);color:var(--ink);
font:17px/1.65 "Iowan Old Style","Palatino Linotype",Palatino,Georgia,serif}
img{max-width:100%;height:auto}
a{color:var(--crimson-d)}
a:hover{color:var(--crimson)}
h1,h2,h3{line-height:1.2;font-weight:600}
h1{font-size:1.9rem;margin:.2em 0 .4em}
h2{font-size:1.35rem;margin:1.6em 0 .5em}
.wrap{max-width:1080px;margin:0 auto;padding:0 20px}
.kicker{font-size:.78rem;letter-spacing:.18em;text-transform:uppercase;color:var(--ink2)}
/* header */
.site-header{background:var(--dark);color:#e8ddc8;border-top:4px solid var(--crimson);
border-bottom:1px solid #3a2f24}
.site-header .wrap{display:flex;align-items:center;gap:1.2rem;flex-wrap:wrap;padding-top:14px;padding-bottom:14px}
.brand{display:flex;align-items:center;gap:.8rem;text-decoration:none;color:#f0e6d2}
.mon{display:grid;place-items:center;width:52px;height:52px;border-radius:50%;
background:radial-gradient(circle at 35% 30%,#c62f2f,var(--crimson-d));color:#f6eedd;
font-size:1.7rem;flex:none;box-shadow:0 0 0 2px #0006 inset}
.brand b{display:block;font-size:1.25rem;letter-spacing:.22em}
.brand i{display:block;font-style:normal;font-size:.72rem;letter-spacing:.14em;color:#b7a887;text-transform:uppercase}
nav.main{display:flex;gap:.25rem;align-items:center;margin-left:auto;flex-wrap:wrap}
nav.main a,nav.main summary{color:#e8ddc8;text-decoration:none;font-size:.85rem;
letter-spacing:.12em;text-transform:uppercase;padding:.5rem .7rem;cursor:pointer}
nav.main a:hover,nav.main summary:hover{color:#fff;background:var(--dark2)}
nav.main details{position:relative}
nav.main summary{list-style:none;display:block}
nav.main summary::-webkit-details-marker{display:none}
nav.main summary::after{content:" ▾";font-size:.7em}
nav.main details ul{position:absolute;left:0;top:100%;z-index:60;margin:0;padding:.45rem 0;
list-style:none;min-width:240px;background:var(--dark2);border:1px solid #3a2f24;box-shadow:0 8px 18px #0007}
nav.main details ul a{display:block;padding:.45rem 1rem;text-transform:none;letter-spacing:.02em;font-size:.95rem}
/* footer */
.site-footer{background:var(--dark);color:#b7a887;margin-top:4rem;border-top:4px solid var(--crimson);
font-size:.95rem}
.site-footer .wrap{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:2rem;padding:2.5rem 20px}
.site-footer h3{color:#e8ddc8;font-size:.8rem;letter-spacing:.18em;text-transform:uppercase;margin:0 0 .8rem}
.site-footer ul{list-style:none;margin:0;padding:0}
.site-footer li{margin:.3rem 0}
.site-footer a{color:#cbbd9e;text-decoration:none}
.site-footer a:hover{color:#fff}
.fineprint{border-top:1px solid #3a2f24;padding:1.2rem 20px 2rem;text-align:center;font-size:.85rem;color:#8d8067}
.fineprint p{max-width:840px;margin:.4rem auto}
/* hero */
.hero{position:relative;overflow:hidden;background:linear-gradient(160deg,#241d16 0%,#191410 70%);
color:#ecdfc6;padding:4.5rem 0 4rem;border-bottom:4px solid var(--crimson)}
.hero .wrap{position:relative;z-index:2;max-width:1080px}
.hero h1{font-size:clamp(2rem,5vw,3.1rem);margin:.3em 0 .35em;color:#f6eedd}
.hero p{max-width:44rem;font-size:1.08rem;color:#cbbd9e}
.hero .bigmon{position:absolute;right:-40px;top:50%;transform:translateY(-50%);z-index:1;
font-size:22rem;color:#2c231a;line-height:1;user-select:none}
/* buttons */
.btn{display:inline-block;padding:.65rem 1.4rem;border:1px solid var(--line);text-decoration:none;
letter-spacing:.08em;font-size:.9rem;text-transform:uppercase}
.btn-amazon{background:var(--crimson);border-color:var(--crimson-d);color:#f8f1e2 !important;
box-shadow:0 2px 0 var(--crimson-d)}
.btn-amazon:hover{background:var(--crimson-d);color:#fff !important}
.btn-ghost{color:#e8ddc8 !important;border-color:#57493a}
.btn-ghost:hover{background:var(--dark2)}
/* cards */
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:1.1rem;margin:1.5rem 0}
.card{background:var(--card);border:1px solid var(--line);display:flex;flex-direction:column;
transition:box-shadow .15s,transform .15s}
.card:hover{box-shadow:0 6px 16px #0002;transform:translateY(-2px)}
.card-media{display:grid;place-items:center;aspect-ratio:1;background:#fff;border-bottom:1px solid var(--line);overflow:hidden}
.card-media img{max-height:100%;object-fit:contain}
.ph{font-size:3.2rem;color:#cdb98c}
.card-body{padding:.7rem .85rem 0.9rem}
.card-body h3{font-size:.98rem;margin:0 0 .3rem;font-weight:600}
.card-body h3 a{text-decoration:none;color:var(--ink)}
.card-body h3 a:hover{color:var(--crimson)}
.card-meta{margin:0;font-size:.78rem;color:var(--ink2);letter-spacing:.05em;text-transform:uppercase}
.card a.stretch::after{content:"";position:absolute;inset:0}
/* category tiles */
.tiles{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:1rem;margin:1.5rem 0}
.tile{position:relative;background:var(--card);border:1px solid var(--line);padding:1rem 1.1rem;text-decoration:none;color:var(--ink)}
.tile:hover{border-color:var(--gold);box-shadow:0 4px 12px #0002}
.tile b{display:block;font-size:1.02rem}
.tile span{font-size:.8rem;color:var(--ink2);letter-spacing:.06em;text-transform:uppercase}
/* breadcrumbs */
.crumbs{font-size:.78rem;letter-spacing:.1em;text-transform:uppercase;color:var(--ink2);margin:1.6rem 0 .8rem}
.crumbs a{color:var(--ink2);text-decoration:none}
.crumbs a:hover{color:var(--crimson)}
/* product */
.product{display:grid;grid-template-columns:minmax(280px,460px) 1fr;gap:2.2rem;margin:1rem 0 2rem}
.product-media{background:#fff;border:1px solid var(--line);display:grid;place-items:center;padding:1rem;align-self:start}
.product-media .ph{font-size:6rem;padding:3rem 0}
.pmeta{color:var(--ink2);font-size:.85rem;letter-spacing:.08em;text-transform:uppercase;margin:.1rem 0 1.2rem}
.cta-box{background:var(--paper2);border:1px solid var(--line);border-left:4px solid var(--crimson);
padding:1.1rem 1.2rem;margin:1.4rem 0}
.cta-note{font-size:.82rem;color:var(--ink2);margin:.7rem 0 0}
.prose{max-width:72ch}
.prose img{display:block;border:1px solid var(--line);background:#fff;padding:4px;margin:1rem 0}
.prose table{border-collapse:collapse}
.prose td{border:1px solid var(--line);padding:.3rem .6rem}
.rule{border:0;border-top:1px solid var(--line);margin:2.5rem 0}
.notice{background:var(--paper2);border:1px solid var(--line);padding:.8rem 1rem;font-size:.9rem;color:var(--ink2)}
/* article list */
.article-list{list-style:none;padding:0}
.article-list li{border-bottom:1px solid var(--line);padding:1rem 0}
.article-list b{font-size:1.1rem}
.article-list p{margin:.25rem 0 0;color:var(--ink2)}
@media(max-width:760px){
  .product{grid-template-columns:1fr}
  nav.main{margin-left:0}
  nav.main details ul{position:static;box-shadow:none;border:0;min-width:0}
  .hero .bigmon{font-size:13rem;right:-60px;opacity:.6}
}
"""

FAVICON = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
           '<circle cx="50" cy="50" r="47" fill="#9e1b1b"/>'
           '<text x="50" y="68" font-size="52" text-anchor="middle" fill="#f4ecdd" '
           'font-family="serif">侍</text></svg>')

def nav_dd(label, items):
    lis = "".join(f'<li><a href="{esc(h)}">{esc(t)}</a></li>' for t, h in items)
    return f"<details><summary>{label}</summary><ul>{lis}</ul></details>"

HEADER = f"""<header class="site-header"><div class="wrap">
<a class="brand" href="/"><span class="mon">侍</span>
<span><b>SAMURAI SUPPLY</b><i>Katana &amp; Japanese Sword Guide</i></span></a>
<nav class="main">{nav_dd("Brands", NAV_BRANDS)}{nav_dd("Gear", NAV_GEAR)}
<a href="/sword_articles/">Articles</a><a href="/about_us/">About</a></nav>
</div></header>"""

def foot_col(title, items):
    lis = "".join(f'<li><a href="{esc(h)}">{esc(t)}</a></li>' for t, h in items)
    return f"<div><h3>{title}</h3><ul>{lis}</ul></div>"

FOOTER = f"""<footer class="site-footer">
<div class="wrap">
{foot_col("Sword Brands", NAV_BRANDS)}
{foot_col("Gear &amp; Training", NAV_GEAR)}
{foot_col("Samurai Supply", [("All Products", "/store/"), ("Sword Articles", "/sword_articles/"),
 ("Testimonials", "/testimonials/"), ("About", "/about_us/"), ("Contact", "/contact_us/"),
 ("Privacy Policy", "/privacy_policy/"), ("Sitemap", "/sitemap/")])}
</div>
<div class="fineprint">
<p><strong>Affiliate disclosure:</strong> SamuraiSupply.com is a participant in the Amazon Services LLC
Associates Program. As an Amazon Associate we earn from qualifying purchases made through links on this
site, at no extra cost to you.</p>
<p>© 2009–2026 SamuraiSupply.com · The archive of the original Samurai Supply sword shop.</p>
</div></footer>"""

def page(title, desc, canonical, body, og_image=None, noindex=False):
    robots = '<meta name="robots" content="noindex">' if noindex else ""
    og_img = f'<meta property="og:image" content="{BASE}{esc(og_image)}">' if og_image else ""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{esc(canonical)}">{robots}
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{esc(canonical)}">{og_img}
<meta name="theme-color" content="#191410">
<link rel="icon" type="image/svg+xml" href="/assets/favicon.svg">
<link rel="stylesheet" href="/assets/site.css">
</head>
<body>
{HEADER}
<main>{body}</main>
{FOOTER}
</body>
</html>"""

def write(relpath, content):
    p = ROOT / relpath
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")

def card(rec):
    href = href_of(rec["file"])
    img = rec.get("thumb") or rec.get("image")
    if img and img_dims(img):
        w, h = img_dims(img)
        media = (f'<img src="{esc(img)}" alt="{esc(rec["name"])}" width="{w}" height="{h}" '
                 f'loading="lazy" decoding="async">')
    else:
        media = '<span class="ph">刀</span>'
    meta = " · ".join(x for x in (rec.get("brand"), rec.get("sku")) if x)
    return (f'<article class="card"><a class="card-media" href="{href}" tabindex="-1" aria-hidden="true">{media}</a>'
            f'<div class="card-body"><h3><a href="{href}">{esc(rec["name"])}</a></h3>'
            f'<p class="card-meta">{esc(meta)}</p></div></article>')

def grid(recs):
    return '<div class="grid">' + "".join(card(r) for r in recs) + "</div>"

def crumbs(*parts):
    out = []
    for label, href in parts:
        if href:
            out.append(f'<a href="{esc(href)}">{esc(label)}</a>')
        else:
            out.append(esc(label))
    return '<nav class="crumbs" aria-label="Breadcrumb">' + " › ".join(out) + "</nav>"

def cta(query, label="Check availability on Amazon"):
    return (f'<div class="cta-box"><a class="btn btn-amazon" href="{esc(amazon_url(query))}" '
            f'rel="sponsored nofollow noopener" target="_blank">{esc(label)} ▸</a>'
            '<p class="cta-note">Opens a live Amazon search for this item. As an Amazon Associate '
            'we earn from qualifying purchases.</p></div>')

# ------------------------------------------------------------------ product pages
ARCHIVE_NOTE = ('<p class="notice">From the Samurai Supply archive — original listing preserved '
                'for reference. Use the Amazon button to find this sword or a comparable one today.</p>')

for rec_list in by_id.values():
    primary = primary_of[rec_list[0]["product_id"]]
    for rec in rec_list:
        is_primary = rec["file"] == primary["file"]
        cat_file = rec["category_file"]
        cat_name = rec["category_name"] or "Store"
        slug = CAT_TO_SLUG.get(cat_file)
        cat_href = f"/{slug}/" if slug else href_of(cat_file)
        name, sku, brand = rec["name"], rec["sku"], rec["brand"]

        if rec["image"] and img_dims(rec["image"]):
            w, h = img_dims(rec["image"])
            media = (f'<img src="{esc(rec["image"])}" alt="{esc(name)}" width="{w}" height="{h}" '
                     f'decoding="async" fetchpriority="high">')
        else:
            media = '<span class="ph">刀</span>'

        meta_bits = " · ".join(x for x in (brand, f"Model {sku}" if sku else "", cat_name) if x)
        desc_html = sanitize(primary["desc_html"])
        related = [r for r in cats[cat_file]["products"] if r["product_id"] != rec["product_id"]][:4]
        related_html = ""
        if related:
            related_html = f'<hr class="rule"><h2>More {esc(cat_name)}</h2>' + grid(related)

        body = f"""<div class="wrap">
{crumbs(("Home", "/"), (cat_name, cat_href), (name, None))}
<div class="product">
<div class="product-media">{media}</div>
<div>
<h1>{esc(name)}</h1>
<p class="pmeta">{esc(meta_bits)}</p>
{ARCHIVE_NOTE}
{cta(amazon_query(rec))}
</div>
</div>
<div class="prose">{desc_html}</div>
{related_html}
</div>"""
        meta_desc = (f"{name}" + (f" by {brand}" if brand else "") +
                     " — original specs and photos from the Samurai Supply archive, "
                     "with links to find it on Amazon.")
        canonical = BASE + href_of(primary["file"])
        write(rec["file"], page(f"{name} | Samurai Supply", meta_desc, canonical, body,
                                og_image=rec["image"], noindex=not is_primary))

# ------------------------------------------------------------------ category pages
def category_body(cat_file, heading, self_href):
    c = cats[cat_file]
    prods = c["products"]
    intro = (f"<p>{len(prods)} listings from the original Samurai Supply catalog. Every page keeps the "
             "original specifications and photos, with a live link to find each piece "
             "— or its closest modern equivalent — on Amazon.</p>")
    return f"""<div class="wrap">
{crumbs(("Home", "/"), (heading, None))}
<h1>{esc(heading)}</h1>
{intro}
{cta(c["name"], "Browse " + c["name"] + " on Amazon")}
{grid(prods)}
</div>"""

for cat_file, c in cats.items():
    slug = CAT_TO_SLUG.get(cat_file)
    heading = SLUG_TITLES.get(slug, c["name"])
    canonical = f"{BASE}/{slug}/" if slug else BASE + href_of(cat_file)
    desc = f"{heading} — {len(c['products'])} archived listings with specs, photos, and Amazon availability links."
    body = category_body(cat_file, heading, canonical)
    noindex = c["name"] == "International Orders"
    write(cat_file, page(f"{heading} | Samurai Supply", desc, canonical, body, noindex=noindex))
    if slug:
        write(f"{slug}/index.html", page(f"{heading} | Samurai Supply", desc, canonical, body))

# ------------------------------------------------------------------ article pages
page_by_dir = {p["dir"]: p for p in pages}

def article_heading_dedupe(content_soup_html, title):
    soup = BeautifulSoup(content_soup_html, "html.parser")
    first = soup.find(["h1", "h2", "h3"])
    if first:
        t = first.get_text(" ", strip=True).lower()
        if t and (t in title.lower() or title.lower() in t):
            first.decompose()
    return str(soup)

for slug, title, blurb in ARTICLES:
    src = page_by_dir.get(slug)
    if not src or not src["content_html"]:
        continue
    content = sanitize(src["content_html"], light=True)
    content = article_heading_dedupe(content, title)
    extra = ""
    if slug == "hanwei-shuihu-tachi" and "store-categories-Hanwei-Shuihu-Tachi_4275006.html" in cats:
        extra = grid(cats["store-categories-Hanwei-Shuihu-Tachi_4275006.html"]["products"])
    if slug == "hakama":
        extra = cta("japanese hakama martial arts", "Browse Hakama on Amazon")
    body = f"""<div class="wrap">
{crumbs(("Home", "/"), ("Articles", "/sword_articles/"), (title, None))}
<h1>{esc(title)}</h1>
<div class="prose">{content}</div>
{extra}
</div>"""
    write(f"{slug}/index.html", page(f"{title} | Samurai Supply", blurb, f"{BASE}/{slug}/", body))

# articles hub
art_items = "".join(
    f'<li><b><a href="/{s}/">{esc(t)}</a></b><p>{esc(bl)}</p></li>'
    for s, t, bl in ARTICLES if page_by_dir.get(s, {}).get("content_html")
)
body = f"""<div class="wrap">
{crumbs(("Home", "/"), ("Articles", None))}
<h1>Sword Articles &amp; Guides</h1>
<p>Guides and lore from the Samurai Supply archive — how to judge a blade, care for it, and
understand the traditions behind it.</p>
<ul class="article-list">{art_items}</ul>
</div>"""
write("sword_articles/index.html", page("Sword Articles & Guides | Samurai Supply",
      "Guides on choosing, using, and caring for samurai swords, from the Samurai Supply archive.",
      f"{BASE}/sword_articles/", body))

# ------------------------------------------------------------------ hand-written pages
brand_tiles = "".join(
    f'<a class="tile" href="{esc(h)}"><b>{esc(t)}</b><span>{len(cats.get(SLUG_TO_CAT.get(h.strip("/")), {"products": []})["products"])} swords</span></a>'
    for t, h in NAV_BRANDS if SLUG_TO_CAT.get(h.strip("/")) in cats
)
gear_tiles = "".join(
    f'<a class="tile" href="{esc(h)}"><b>{esc(t)}</b><span>{len(cats.get(SLUG_TO_CAT.get(h.strip("/")), {"products": []})["products"])} items</span></a>'
    for t, h in NAV_GEAR if SLUG_TO_CAT.get(h.strip("/")) in cats
)
featured = []
for slug in ("musashi_samurai_swords", "ten_ryu_samurai_swords", "ryumon_samurai_swords",
             "hanwei_paul_chen_samurai_swords", "masahiro_samurai_swords", "bushido_samurai_swords",
             "thaitsuki_samurai_sword", "handmade_samurai_swords"):
    prods = cats.get(SLUG_TO_CAT[slug], {}).get("products", [])
    with_thumb = [r for r in prods if r.get("thumb") and img_dims(r["thumb"])]
    pick = next((r for r in with_thumb if "katana" in r["name"].lower()), with_thumb[0] if with_thumb else None)
    if pick:
        featured.append(pick)

home_body = f"""<section class="hero"><span class="bigmon" aria-hidden="true">侍</span>
<div class="wrap">
<p class="kicker">Est. 2009 · The sword shop, reborn as a guide</p>
<h1>The Way of the Sword,<br>Faithfully Catalogued</h1>
<p>Samurai Supply spent years selling katana, bokken, and sword gear from the best-known forges.
The full catalog lives on here — every blade documented with its original specs and photos —
now paired with live Amazon links so you can still find the steel you're after.</p>
<p><a class="btn btn-amazon" href="/store/">Browse the full catalog ▸</a>
<a class="btn btn-ghost" href="/sword_articles/">Read the sword guides</a></p>
</div></section>
<div class="wrap">
<h2>Sword Brands &amp; Forges</h2>
<div class="tiles">{brand_tiles}</div>
<h2>Training Gear &amp; Accessories</h2>
<div class="tiles">{gear_tiles}</div>
<h2>From the Archive</h2>
{grid(featured)}
<hr class="rule">
<div class="prose">
<h2>About this site</h2>
<p>SamuraiSupply.com was an online sword shop from 2009 to the mid-2010s. The store has closed,
but its catalog — hundreds of katana, wakizashi, bokken, tsuba, and training supplies — remains
one of the better references for production Japanese-style swords of that era. Each listing keeps the
original description and measurements, and links to a current Amazon search so you can check today's
availability and pricing. See our <a href="/sword_articles/">articles</a> to learn what separates a
functional blade from a wall-hanger.</p>
</div>
</div>"""
write("index.html", page("Samurai Supply | Katana, Samurai & Japanese Sword Guide",
      "The archived Samurai Supply sword catalog — katana, bokken, and sword gear from Musashi, "
      "Hanwei, Ryumon, Ten Ryu and more, with live Amazon availability links.",
      BASE + "/", home_body))

# all products (store/)
cat_sections = []
for cat_file, c in sorted(cats.items(), key=lambda kv: kv[1]["name"]):
    if c["name"] == "International Orders":
        continue
    slug = CAT_TO_SLUG.get(cat_file)
    heading = SLUG_TITLES.get(slug, c["name"])
    href = f"/{slug}/" if slug else href_of(cat_file)
    cat_sections.append(f'<h2 id="{esc(slug or cat_file)}"><a href="{esc(href)}">{esc(heading)}</a></h2>' + grid(c["products"]))
body = f"""<div class="wrap">
{crumbs(("Home", "/"), ("All Products", None))}
<h1>The Complete Catalog</h1>
<p>Every listing from the original Samurai Supply store, organized by brand and category.</p>
{''.join(cat_sections)}
</div>"""
write("store/index.html", page("All Products | Samurai Supply",
      "The complete archived Samurai Supply catalog — every sword, bokken, and accessory.",
      f"{BASE}/store/", body))

# about
body = f"""<div class="wrap">
{crumbs(("Home", "/"), ("About", None))}
<h1>About Samurai Supply</h1>
<div class="prose">
<p>Samurai Supply opened in 2009 as a specialty online sword shop, carrying functional and decorative
Japanese-style swords from forges like Musashi, Hanwei Paul Chen, Ryumon, Ten Ryu, Masahiro, Kawashima,
and Thaitsuki, along with bokken, kendo equipment, hakama, tsuba, and sword care supplies.</p>
<p>The store itself has since closed — but rather than let a decade of product research disappear,
we've preserved the entire catalog as a reference archive. Every listing keeps its original
specifications, measurements, and photographs.</p>
<p>Because these exact production runs come and go, each page now links to a live Amazon search for the
item so you can check current availability and pricing. Links to Amazon are affiliate links: as an
Amazon Associate we earn from qualifying purchases, at no additional cost to you. That's what keeps
this archive online.</p>
<p>Questions or corrections? <a href="/contact_us/">Contact us</a>.</p>
</div>
</div>"""
write("about_us/index.html", page("About | Samurai Supply",
      "The story of Samurai Supply — a 2009-era online sword shop preserved as a katana reference archive.",
      f"{BASE}/about_us/", body))

# contact
body = f"""<div class="wrap">
{crumbs(("Home", "/"), ("Contact", None))}
<h1>Contact</h1>
<div class="prose">
<p>Samurai Supply is no longer an operating store, so we can't take orders or process returns —
but we're glad to hear about broken links, incorrect specs, or suggestions for the archive.</p>
<p>Email: <a href="mailto:info@samuraisupply.com">info@samuraisupply.com</a></p>
<p>Looking to buy a sword? Every product page links to a current Amazon search for that item.</p>
</div>
</div>"""
write("contact_us/index.html", page("Contact | Samurai Supply",
      "Contact the Samurai Supply archive.", f"{BASE}/contact_us/", body))

# privacy
body = f"""<div class="wrap">
{crumbs(("Home", "/"), ("Privacy Policy", None))}
<h1>Privacy Policy</h1>
<div class="prose">
<p>SamuraiSupply.com is a static reference site. We do not require accounts, do not collect personal
information, and do not use tracking cookies of our own.</p>
<h2>Affiliate links</h2>
<p>SamuraiSupply.com is a participant in the Amazon Services LLC Associates Program, an affiliate
advertising program designed to provide a means for sites to earn advertising fees by advertising and
linking to Amazon.com. When you click a product link on this site, Amazon may set cookies in your
browser to attribute your visit; those cookies are governed by
<a href="https://www.amazon.com/privacy" rel="nofollow noopener" target="_blank">Amazon's privacy policy</a>.</p>
<h2>Hosting</h2>
<p>This site is hosted on GitHub Pages, which may log standard web-server request data (such as IP
addresses) for security and operational purposes, per
<a href="https://docs.github.com/en/site-policy/privacy-policies" rel="nofollow noopener" target="_blank">GitHub's privacy statement</a>.</p>
<p>Questions? <a href="/contact_us/">Contact us</a>.</p>
</div>
</div>"""
write("privacy_policy/index.html", page("Privacy Policy | Samurai Supply",
      "Privacy policy for SamuraiSupply.com.", f"{BASE}/privacy_policy/", body))

# sitemap page
cat_links = "".join(f'<li><a href="/{s}/">{esc(SLUG_TITLES[s])}</a></li>' for s in sorted(SLUG_TO_CAT) if SLUG_TO_CAT[s] in cats)
art_links = "".join(f'<li><a href="/{s}/">{esc(t)}</a></li>' for s, t, _ in ARTICLES if page_by_dir.get(s, {}).get("content_html"))
body = f"""<div class="wrap">
{crumbs(("Home", "/"), ("Sitemap", None))}
<h1>Sitemap</h1>
<div class="prose">
<h2>Categories</h2><ul>{cat_links}</ul>
<h2>Articles</h2><ul>{art_links}</ul>
<h2>Site</h2><ul>
<li><a href="/store/">All Products</a></li><li><a href="/about_us/">About</a></li>
<li><a href="/contact_us/">Contact</a></li><li><a href="/privacy_policy/">Privacy Policy</a></li>
</ul>
</div></div>"""
write("sitemap/index.html", page("Sitemap | Samurai Supply", "All sections of SamuraiSupply.com.",
      f"{BASE}/sitemap/", body))

# 404
body = """<div class="wrap" style="text-align:center;padding:4rem 20px">
<p class="ph" style="font-size:5rem;margin:0">刀</p>
<h1>Page Not Found</h1>
<p>The blade you seek has been sheathed. Try the <a href="/store/">full catalog</a> or return
<a href="/">home</a>.</p>
</div>"""
write("404.html", page("Page Not Found | Samurai Supply", "Page not found.", f"{BASE}/404.html", body, noindex=True))

# redirect stubs
def redirect_stub(target):
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Moved | Samurai Supply</title>
<meta http-equiv="refresh" content="0; url={target}">
<link rel="canonical" href="{BASE}{target}"><meta name="robots" content="noindex">
</head><body><p>This page has moved: <a href="{target}">continue</a>.</p></body></html>"""

for slug, target in REDIRECTS.items():
    write(f"{slug}/index.html", redirect_stub(target))
write("store-categories-Special-Orders_4277816.html", redirect_stub("/store/"))
write("store/show_product/index.html", redirect_stub("/store/"))
write("store/shopcart/index.html", redirect_stub("/store/"))
write("store/checkout/index.html", redirect_stub("/store/"))
write("store/list_products/index.html", redirect_stub("/store/"))

# assets
write("assets/site.css", CSS)
write("assets/favicon.svg", FAVICON)
write(".nojekyll", "")
write("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n")

# sitemap.xml — primary products, categories, articles, core pages
urls = [f"{BASE}/", f"{BASE}/store/", f"{BASE}/sword_articles/", f"{BASE}/about_us/",
        f"{BASE}/contact_us/", f"{BASE}/privacy_policy/", f"{BASE}/sitemap/", f"{BASE}/testimonials/"]
urls += [f"{BASE}/{s}/" for s in sorted(SLUG_TO_CAT) if SLUG_TO_CAT[s] in cats]
urls += [f"{BASE}/{s}/" for s, _, _ in ARTICLES if page_by_dir.get(s, {}).get("content_html") and f"{BASE}/{s}/" not in urls]
for pid, rec in sorted(primary_of.items()):
    if rec["category_name"] == "International Orders":
        continue
    urls.append(BASE + href_of(rec["file"]))
urls = list(dict.fromkeys(urls))
sm = ['<?xml version="1.0" encoding="UTF-8"?>',
      '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
sm += [f"<url><loc>{html_mod.escape(u)}</loc></url>" for u in urls]
sm.append("</urlset>")
write("sitemap.xml", "\n".join(sm))

print(f"done. products={len(catalog)} categories={len(cats)} sitemap_urls={len(urls)}")
