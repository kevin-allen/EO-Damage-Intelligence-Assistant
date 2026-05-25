"""
Generate scenario_browser/index.html — a candidate browser used to pick the 12
scenarios for the demo catalog.

Reads xView2 test-split labels, computes a per-tile severity_index from GT
damage classes (per software_architecture.md §2.3), shortlists candidates per
disaster type bucketed by severity (minor / moderate / severe / catastrophic
per arch §2.4), and renders an HTML page with pre/post thumbnails + damage
breakdowns. Thumbnails are produced under scenario_browser/thumbs/.

Run inside the app container (PIL only — no GPU, no torch).
"""
from __future__ import annotations

import html
import json
import os
from collections import Counter, defaultdict
from glob import glob
from pathlib import Path

from PIL import Image


XVIEW2_TEST_LABELS = Path("/data/xView2/test/labels")
XVIEW2_TEST_IMAGES = Path("/data/xView2/test/images")

REPO = Path(__file__).resolve().parent.parent
OUT_DIR = REPO / "scenario_browser"
THUMB_DIR = OUT_DIR / "thumbs"
FULL_DIR = OUT_DIR / "full"
OUT_HTML = OUT_DIR / "index.html"

WEIGHTS = {"no-damage": 0.0, "minor-damage": 0.33, "major-damage": 0.66, "destroyed": 1.0}
EVENTS_BY_DTYPE = {
    "hurricane": ["hurricane-florence", "hurricane-harvey", "hurricane-matthew", "hurricane-michael"],
    "wildfire": ["santa-rosa-wildfire", "socal-fire"],
    "flood": ["midwest-flooding"],
    "earthquake-tsunami": ["mexico-earthquake", "palu-tsunami"],
}
BUCKETS = ["minor", "moderate", "severe", "catastrophic"]
MIN_BUILDINGS = {"hurricane": 20, "wildfire": 20, "flood": 5, "earthquake-tsunami": 20}
PER_BUCKET = 3
THUMB_SIZE = (512, 512)
FULL_SIZE = (1024, 1024)


def severity_bucket(sev: float) -> str:
    if sev < 0.25:
        return "minor"
    if sev < 0.50:
        return "moderate"
    if sev < 0.75:
        return "severe"
    return "catastrophic"


def scan_tiles() -> list[dict]:
    rows: list[dict] = []
    for dtype, events in EVENTS_BY_DTYPE.items():
        for ev in events:
            for path in sorted(glob(str(XVIEW2_TEST_LABELS / f"{ev}_*_post_disaster.json"))):
                d = json.load(open(path))
                feats = d["features"]["xy"]
                counts = Counter(f["properties"].get("subtype", "?") for f in feats)
                classified = sum(counts[k] for k in WEIGHTS)
                if classified == 0:
                    continue
                sev = sum(WEIGHTS[k] * counts[k] for k in WEIGHTS) / classified
                tile_id = os.path.basename(path).replace("_post_disaster.json", "")
                rows.append(
                    {
                        "dtype": dtype,
                        "event": ev,
                        "tile_id": tile_id,
                        "total_features": sum(counts.values()),
                        "classified": classified,
                        "sev": sev,
                        "counts": dict(counts),
                    }
                )
    return rows


def shortlist(rows: list[dict]) -> dict[str, dict[str, list[dict]]]:
    pool: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for r in rows:
        if r["classified"] < MIN_BUILDINGS[r["dtype"]]:
            continue
        pool[r["dtype"]][severity_bucket(r["sev"])].append(r)

    result: dict[str, dict[str, list[dict]]] = defaultdict(dict)
    for dtype, by_b in pool.items():
        for b in BUCKETS:
            items = sorted(by_b.get(b, []), key=lambda r: -r["classified"])
            seen_events, picked = set(), []
            for it in items:
                if it["event"] not in seen_events and len(picked) < PER_BUCKET:
                    picked.append(it)
                    seen_events.add(it["event"])
            if len(picked) < PER_BUCKET:
                for it in items:
                    if it not in picked:
                        picked.append(it)
                    if len(picked) >= PER_BUCKET:
                        break
            result[dtype][b] = picked
    return result


def ensure_thumbnail(tile_id: str, phase: str) -> Path:
    THUMB_DIR.mkdir(parents=True, exist_ok=True)
    out = THUMB_DIR / f"{tile_id}_{phase}.jpg"
    if not out.exists():
        src = XVIEW2_TEST_IMAGES / f"{tile_id}_{phase}_disaster.png"
        im = Image.open(src).convert("RGB")
        im.thumbnail(THUMB_SIZE, Image.LANCZOS)
        im.save(out, "JPEG", quality=82, optimize=True)
    return out


def ensure_full(tile_id: str, phase: str) -> Path:
    FULL_DIR.mkdir(parents=True, exist_ok=True)
    out = FULL_DIR / f"{tile_id}_{phase}.jpg"
    if not out.exists():
        src = XVIEW2_TEST_IMAGES / f"{tile_id}_{phase}_disaster.png"
        im = Image.open(src).convert("RGB")
        if im.size[0] > FULL_SIZE[0] or im.size[1] > FULL_SIZE[1]:
            im.thumbnail(FULL_SIZE, Image.LANCZOS)
        im.save(out, "JPEG", quality=90, optimize=True)
    return out


DAMAGE_ORDER = ["no-damage", "minor-damage", "major-damage", "destroyed", "un-classified"]
DAMAGE_COLOR = {
    "no-damage": "#3b8132",
    "minor-damage": "#d4a017",
    "major-damage": "#d96b1f",
    "destroyed": "#b81e1e",
    "un-classified": "#7a7a7a",
}


def render_breakdown(counts: dict[str, int], classified: int) -> str:
    rows = []
    for cls in DAMAGE_ORDER:
        n = counts.get(cls, 0)
        if n == 0:
            continue
        pct = 100.0 * n / classified if cls != "un-classified" and classified else 100.0 * n / sum(counts.values())
        color = DAMAGE_COLOR[cls]
        rows.append(
            f'<tr><td><span class="dot" style="background:{color}"></span>{html.escape(cls)}</td>'
            f"<td class=num>{n}</td><td class=num>{pct:.1f}%</td></tr>"
        )
    return "<table class=brk>" + "".join(rows) + "</table>"


def render_card(r: dict) -> str:
    tile_id = r["tile_id"]
    ensure_thumbnail(tile_id, "pre")
    ensure_thumbnail(tile_id, "post")
    ensure_full(tile_id, "pre")
    ensure_full(tile_id, "post")
    breakdown = render_breakdown(r["counts"], r["classified"])
    return f"""
<div class="card" data-tile="{html.escape(tile_id)}">
  <div class="card-head">
    <div class="tile-id">{html.escape(tile_id)}</div>
    <div class="meta">sev <b>{r["sev"]:.2f}</b> &middot; {r["classified"]} buildings</div>
  </div>
  <div class="imgs">
    <figure>
      <img class="zoomable" loading="lazy" src="thumbs/{tile_id}_pre.jpg"
           data-full="full/{tile_id}_pre.jpg" data-pair="full/{tile_id}_post.jpg"
           data-label="{html.escape(tile_id)} — pre" alt="pre">
      <figcaption>pre</figcaption>
    </figure>
    <figure>
      <img class="zoomable" loading="lazy" src="thumbs/{tile_id}_post.jpg"
           data-full="full/{tile_id}_post.jpg" data-pair="full/{tile_id}_pre.jpg"
           data-label="{html.escape(tile_id)} — post" alt="post">
      <figcaption>post</figcaption>
    </figure>
  </div>
  {breakdown}
</div>"""


def render_bucket(dtype: str, bucket: str, items: list[dict]) -> str:
    if not items:
        return f'<section class="bucket empty"><h3>{bucket}</h3><div class=note>no candidates above threshold</div></section>'
    cards = "\n".join(render_card(r) for r in items)
    return f'<section class="bucket"><h3>{bucket} <span class=count>({len(items)})</span></h3><div class="cards">{cards}</div></section>'


def render_dtype(dtype: str, by_b: dict[str, list[dict]]) -> str:
    body = "\n".join(render_bucket(dtype, b, by_b.get(b, [])) for b in BUCKETS)
    return f'<article class="dtype"><h2 id="{dtype}">{dtype}</h2>{body}</article>'


CSS = """
* { box-sizing: border-box; }
body { font: 14px/1.4 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
       margin: 0; padding: 24px; background: #f5f5f7; color: #1d1d1f; }
h1 { margin: 0 0 4px; }
.subtitle { color: #555; margin-bottom: 20px; }
nav { position: sticky; top: 0; background: #f5f5f7; padding: 8px 0 12px; margin-bottom: 12px;
      border-bottom: 1px solid #ddd; z-index: 10; }
nav a { margin-right: 16px; color: #06c; text-decoration: none; font-weight: 500; }
nav a:hover { text-decoration: underline; }
article.dtype { background: white; border-radius: 8px; padding: 16px 20px; margin-bottom: 24px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.06); }
article.dtype h2 { margin: 0 0 12px; text-transform: capitalize; }
section.bucket { margin-top: 12px; }
section.bucket h3 { margin: 8px 0; text-transform: capitalize; font-size: 14px; color: #333;
                    border-left: 4px solid #aaa; padding-left: 8px; }
section.bucket .count { color: #888; font-weight: normal; font-size: 12px; }
section.bucket.empty .note { color: #999; font-style: italic; margin-left: 12px; font-size: 12px; }
.cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); gap: 12px; }
.card { border: 1px solid #e0e0e0; border-radius: 6px; padding: 10px; background: #fafafa; }
.card-head { display: flex; justify-content: space-between; gap: 8px; align-items: baseline;
             margin-bottom: 6px; font-size: 12px; }
.tile-id { font-family: ui-monospace, "SF Mono", Menlo, monospace; font-size: 11px; color: #444; }
.meta { color: #666; }
.imgs { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; margin-bottom: 8px; }
.imgs figure { margin: 0; }
.imgs img { width: 100%; height: auto; display: block; border-radius: 4px; }
.imgs img.zoomable { cursor: zoom-in; transition: transform 0.08s; }
.imgs img.zoomable:hover { transform: scale(1.02); }
.imgs figcaption { font-size: 10px; color: #666; text-align: center; padding-top: 2px; }

/* lightbox */
#lightbox { position: fixed; inset: 0; background: rgba(0,0,0,0.92); display: none;
            z-index: 1000; cursor: zoom-out;
            flex-direction: column; align-items: center; justify-content: center; padding: 20px; }
#lightbox.open { display: flex; }
#lightbox .lb-imgs { display: flex; gap: 12px; max-width: 100%; max-height: calc(100vh - 90px);
                     align-items: center; justify-content: center; }
#lightbox .lb-imgs figure { margin: 0; display: flex; flex-direction: column; align-items: center; }
#lightbox .lb-imgs img { max-width: 46vw; max-height: calc(100vh - 110px); width: auto; height: auto;
                         border-radius: 6px; box-shadow: 0 4px 20px rgba(0,0,0,0.5); }
#lightbox .lb-imgs figcaption { color: #ddd; font-size: 13px; padding-top: 6px; }
#lightbox .lb-label { color: #fff; font-family: ui-monospace, "SF Mono", Menlo, monospace;
                      font-size: 13px; margin-bottom: 14px; }
#lightbox .lb-hint { position: absolute; bottom: 14px; left: 0; right: 0; text-align: center;
                     color: #999; font-size: 11px; }
@media (max-width: 720px) {
  #lightbox .lb-imgs { flex-direction: column; }
  #lightbox .lb-imgs img { max-width: 92vw; max-height: 40vh; }
}
table.brk { width: 100%; border-collapse: collapse; font-size: 12px; }
table.brk td { padding: 2px 6px; }
table.brk td.num { text-align: right; font-variant-numeric: tabular-nums; color: #333; }
.dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px;
       vertical-align: middle; }
.severity-key { font-size: 12px; color: #555; margin-top: 4px; }
.severity-key code { background: #eee; padding: 1px 5px; border-radius: 3px; }
"""


def build_html(shortlist_data: dict[str, dict[str, list[dict]]]) -> str:
    sev_key = (
        "<div class=severity-key>"
        "<b>severity_index</b> = (0·no-damage + 0.33·minor + 0.66·major + 1.0·destroyed) / classified buildings"
        " &nbsp;|&nbsp; buckets: <code>minor &lt;0.25</code>, "
        "<code>moderate &lt;0.50</code>, <code>severe &lt;0.75</code>, "
        "<code>catastrophic ≥0.75</code>"
        "</div>"
    )
    body = "\n".join(render_dtype(d, shortlist_data[d]) for d in EVENTS_BY_DTYPE)
    nav_links = " ".join(f'<a href="#{d}">{d}</a>' for d in EVENTS_BY_DTYPE)
    return f"""<!doctype html>
<html lang=en>
<head>
<meta charset=utf-8>
<title>xView2 scenario browser — candidate tiles</title>
<style>{CSS}</style>
</head>
<body>
<h1>xView2 scenario browser</h1>
<div class=subtitle>
  Candidate tiles for the 12-scenario catalog. Sourced from the <b>test split</b>.
  Damage stats come from GT labels (not model predictions).
  <i>Click any image to view both pre and post at full size.</i>
</div>
{sev_key}
<nav>{nav_links}</nav>
{body}

<div id="lightbox" role="dialog" aria-hidden="true">
  <div class="lb-label" id="lb-label"></div>
  <div class="lb-imgs">
    <figure><img id="lb-pre" alt="pre"><figcaption>pre</figcaption></figure>
    <figure><img id="lb-post" alt="post"><figcaption>post</figcaption></figure>
  </div>
  <div class="lb-hint">click anywhere or press Esc to close</div>
</div>

<script>
(function() {{
  const lb = document.getElementById('lightbox');
  const lbPre = document.getElementById('lb-pre');
  const lbPost = document.getElementById('lb-post');
  const lbLabel = document.getElementById('lb-label');

  function open(img) {{
    const full = img.dataset.full;
    const pair = img.dataset.pair;
    const label = img.dataset.label || '';
    // Show pre on the left, post on the right regardless of which was clicked.
    const clickedIsPre = full.endsWith('_pre.jpg');
    lbPre.src  = clickedIsPre ? full : pair;
    lbPost.src = clickedIsPre ? pair : full;
    lbLabel.textContent = label.replace(/ — (pre|post)$/, '');
    lb.classList.add('open');
    lb.setAttribute('aria-hidden', 'false');
  }}
  function close() {{
    lb.classList.remove('open');
    lb.setAttribute('aria-hidden', 'true');
    lbPre.src = ''; lbPost.src = '';
  }}

  document.querySelectorAll('img.zoomable').forEach(img => {{
    img.addEventListener('click', () => open(img));
  }});
  lb.addEventListener('click', close);
  document.addEventListener('keydown', e => {{
    if (e.key === 'Escape' && lb.classList.contains('open')) close();
  }});
}})();
</script>
</body>
</html>
"""


def main() -> None:
    rows = scan_tiles()
    short = shortlist(rows)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_HTML.write_text(build_html(short), encoding="utf-8")
    n_cards = sum(len(items) for by_b in short.values() for items in by_b.values())
    print(f"wrote {OUT_HTML}  ({n_cards} candidate cards)")


if __name__ == "__main__":
    main()
