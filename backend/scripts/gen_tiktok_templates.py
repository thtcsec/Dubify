"""Generate tiktok_news.html for all studio aspect folders."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "templates" / "studio"

SIZES = {
    "1080x1920": (1080, 1920, 72, 48, "72px 56px 140px"),
    "1920x1080": (1920, 1080, 64, 42, "56px 72px 72px"),
    "1080x1440": (1080, 1440, 68, 44, "64px 56px 120px"),
    "1440x1080": (1440, 1080, 60, 40, "48px 64px 64px"),
    "1080x1080": (1080, 1080, 62, 42, "56px 56px 72px"),
}


def template(w: int, h: int, title_px: int, hook_px: int, pad: str) -> str:
    is_land = w > h
    title_align = "left" if is_land else "center"
    card_width = "55%" if is_land else "92%"
    justify = "flex-start" if is_land else "flex-end"
    return f"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8"/>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{width:{w}px;height:{h}px;overflow:hidden;font-family:'Segoe UI',Arial,sans-serif;background:#050a18}}
.scene{{width:{w}px;height:{h}px;position:relative;overflow:hidden}}
.bg{{position:absolute;inset:0}}
.bg img{{width:100%;height:100%;object-fit:cover;animation:kenBurns 14s ease-out forwards}}
.overlay{{position:absolute;inset:0;background:linear-gradient(180deg,rgba(5,10,24,.5),rgba(2,6,23,.94))}}
.glow{{position:absolute;width:480px;height:480px;border-radius:50%;background:radial-gradient(circle,rgba(56,189,248,.25),transparent 70%);top:-100px;right:-60px}}
.page{{position:relative;z-index:2;height:100%;padding:{pad};display:flex;flex-direction:column;justify-content:{justify};gap:32px}}
.title{{font-size:{title_px}px;font-weight:900;line-height:1.1;color:#fff;text-align:{title_align};text-shadow:0 8px 36px rgba(0,0,0,.6);animation:titlePop .9s cubic-bezier(.22,1,.36,1) .12s both}}
.hook-card{{max-width:{card_width};background:rgba(255,255,255,.13);border:1px solid rgba(255,255,255,.28);backdrop-filter:blur(18px);border-radius:24px;padding:36px 32px;animation:cardPop 1s cubic-bezier(.22,1,.36,1) .28s both;box-shadow:0 28px 70px rgba(0,0,0,.45)}}
.hook{{font-size:{hook_px}px;font-weight:700;color:#f8fafc;line-height:1.45;white-space:pre-line}}
.bar{{width:120px;height:6px;border-radius:3px;background:linear-gradient(90deg,#38bdf8,#a78bfa);margin-top:18px}}
@keyframes titlePop{{from{{opacity:0;transform:translateY(32px)}}to{{opacity:1;transform:translateY(0)}}}}
@keyframes cardPop{{from{{opacity:0;transform:translateY(56px) scale(.94)}}to{{opacity:1;transform:translateY(0) scale(1)}}}}
@keyframes kenBurns{{from{{transform:scale(1.02)}}to{{transform:scale(1.09)}}}}
</style>
</head>
<body>
<div class="scene">
  <div class="bg"><img src="{{IMAGE_URL}}" alt=""/></div>
  <motion.div class="overlay"></div>
  <div class="glow"></div>
  <div class="page">
    {{TITLE_BLOCK}}
    <div class="hook-card"><div class="hook">{{TEXT}}</div></div>
  </div>
</div>
</body>
</html>
"""


def main() -> None:
    for folder, (w, h, ts, hs, pad) in SIZES.items():
        html = template(w, h, ts, hs, pad)
        html = html.replace("<motion.div", "<div").replace("</motion.div>", "</div>")
        out_dir = ROOT / folder
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "tiktok_news.html").write_text(html, encoding="utf-8")
        print("wrote", out_dir / "tiktok_news.html")


if __name__ == "__main__":
    main()
