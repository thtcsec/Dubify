"""Generate tiktok_news + tiktok_news_pill.html for all studio aspect folders."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "templates" / "studio"

SOCIAL_CSS = """
.social-overlay.tiktok-follow{position:absolute;left:48px;bottom:120px;z-index:20;display:flex;align-items:center;gap:16px;
  padding:14px 20px;border-radius:999px;background:rgba(0,0,0,.72);border:1px solid rgba(255,255,255,.2)}
.tt-avatar,.tt-avatar-fallback{width:56px;height:56px;border-radius:50%;object-fit:cover;border:2px solid #fff}
.tt-avatar-fallback{background:linear-gradient(135deg,#38bdf8,#a78bfa)}
.tt-meta{display:flex;flex-direction:column;gap:6px}
.tt-handle{font-size:26px;font-weight:800;color:#fff}
.tt-follow-btn{align-self:flex-start;padding:6px 18px;border-radius:8px;background:#fe2c55;color:#fff;font-weight:700;font-size:18px}
.social-overlay.yt-lower-third{position:absolute;left:48px;bottom:72px;z-index:20;display:flex;align-items:center;gap:18px;
  padding:16px 22px;border-radius:12px;background:linear-gradient(90deg,rgba(204,0,0,.92),rgba(180,0,0,.75));max-width:88%}
.yt-avatar,.yt-avatar-fallback{width:64px;height:64px;border-radius:50%;object-fit:cover;border:2px solid rgba(255,255,255,.9)}
.yt-avatar-fallback{background:#111}
.yt-text{display:flex;flex-direction:column;gap:4px;flex:1;min-width:0}
.yt-channel{font-size:28px;font-weight:800;color:#fff}
.yt-subline{font-size:20px;color:rgba(255,255,255,.88)}
.yt-subscribe{padding:10px 22px;border-radius:4px;background:#fff;color:#c00;font-weight:800;font-size:18px;white-space:nowrap}
"""

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
.page{{position:relative;z-index:2;height:100%;padding:{pad};display:flex;flex-direction:column;justify-content:center;align-items:center;gap:28px;text-align:center}}
.title{{font-size:{title_px}px;font-weight:900;line-height:1.1;color:#fff;text-align:{title_align};text-shadow:0 8px 36px rgba(0,0,0,.6);animation:titlePop .9s cubic-bezier(.22,1,.36,1) .12s both}}
.hook-card{{max-width:{card_width};background:rgba(255,255,255,.13);border:1px solid rgba(255,255,255,.28);backdrop-filter:blur(18px);border-radius:24px;padding:36px 32px;animation:cardPop 1s cubic-bezier(.22,1,.36,1) .28s both;box-shadow:0 28px 70px rgba(0,0,0,.45)}}
.hook{{font-size:{hook_px}px;font-weight:700;color:#f8fafc;line-height:1.45;white-space:pre-line}}
.bar{{width:120px;height:6px;border-radius:3px;background:linear-gradient(90deg,#38bdf8,#a78bfa);margin-top:18px}}
@keyframes titlePop{{from{{opacity:0;transform:translateY(32px)}}to{{opacity:1;transform:translateY(0)}}}}
@keyframes cardPop{{from{{opacity:0;transform:translateY(56px) scale(.94)}}to{{opacity:1;transform:translateY(0) scale(1)}}}}
@keyframes kenBurns{{from{{transform:scale(1.02)}}to{{transform:scale(1.09)}}}}
{SOCIAL_CSS}
</style>
</head>
<body>
<div class="scene">
  <div class="bg"><img src="{{IMAGE_URL}}" alt=""/></div>
  <div class="overlay"></div>
  <div class="glow"></div>
  <div class="page">
    {{TITLE_BLOCK}}
    <div class="hook-card"><div class="hook">{{TEXT}}</div></div>
  </div>
  {{SOCIAL_OVERLAY}}
</div>
</body>
</html>
"""


def pill_template(w: int, h: int, title_px: int, hook_px: int, pad: str) -> str:
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
.overlay{{position:absolute;inset:0;background:linear-gradient(180deg,rgba(5,10,24,.55),rgba(2,6,23,.92))}}
.page{{position:relative;z-index:2;height:100%;padding:{pad};display:flex;flex-direction:column;justify-content:center;align-items:center;gap:24px;text-align:center}}
.title{{font-size:{title_px}px;font-weight:900;line-height:1.1;color:#fff;text-align:{title_align};
  text-shadow:0 8px 36px rgba(0,0,0,.6);animation:titlePop .9s cubic-bezier(.22,1,.36,1) .1s both}}
.caption-pill{{max-width:{card_width};animation:cardPop 1s cubic-bezier(.22,1,.36,1) .25s both}}
.pill-inner{{background:rgba(0,0,0,.62);border-radius:999px;padding:32px 40px;border:2px solid rgba(255,255,255,.22);
  box-shadow:0 24px 60px rgba(0,0,0,.5)}}
.hook{{font-size:{hook_px}px;font-weight:800;color:#fff;line-height:1.4;white-space:pre-line;text-align:center}}
.bar{{width:100px;height:5px;border-radius:3px;background:linear-gradient(90deg,#facc15,#fe2c55);margin:16px auto 0}}
@keyframes titlePop{{from{{opacity:0;transform:translateY(28px)}}to{{opacity:1;transform:translateY(0)}}}}
@keyframes cardPop{{from{{opacity:0;transform:translateY(48px) scale(.95)}}to{{opacity:1;transform:translateY(0) scale(1)}}}}
@keyframes kenBurns{{from{{transform:scale(1.02)}}to{{transform:scale(1.08)}}}}
{SOCIAL_CSS}
</style>
</head>
<body>
<div class="scene">
  <div class="bg"><img src="{{IMAGE_URL}}" alt=""/></div>
  <div class="overlay"></div>
  <div class="page">
    {{TITLE_BLOCK}}
    <div class="caption-pill"><div class="pill-inner"><div class="hook">{{TEXT}}</div><div class="bar"></div></div>
  </div>
  {{SOCIAL_OVERLAY}}
</div>
</body>
</html>
"""


def _fix_placeholders(html: str) -> str:
    return html.replace("<div", "<div").replace("</div>", "</div>")


def _inject_social_css(html: str) -> str:
    marker = "{SOCIAL_CSS}"
    if marker in html:
        return html.replace(marker, SOCIAL_CSS.strip())
    return html.replace("</style>", SOCIAL_CSS + "</style>", 1)


def main() -> None:
    for folder, (w, h, ts, hs, pad) in SIZES.items():
        out_dir = ROOT / folder
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "tiktok_news.html").write_text(
            _fix_placeholders(_inject_social_css(template(w, h, ts, hs, pad))), encoding="utf-8"
        )
        (out_dir / "tiktok_news_pill.html").write_text(
            _fix_placeholders(_inject_social_css(pill_template(w, h, ts, hs, pad))), encoding="utf-8"
        )
        print("wrote", out_dir / "tiktok_news.html", "and tiktok_news_pill.html")


if __name__ == "__main__":
    main()
