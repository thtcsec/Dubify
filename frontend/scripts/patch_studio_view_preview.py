from pathlib import Path

p = Path(__file__).resolve().parents[1] / "src/views/StudioView.tsx"
snippet = Path(__file__).resolve().parents[1] / "src/views/_studio_preview_snippet.tsx"
lines = p.read_text(encoding="utf-8").splitlines(keepends=True)
ins = snippet.read_text(encoding="utf-8")
new = lines[:227] + [ins] + lines[285:]
text = "".join(new)
old = '                {/* Settings & Generation Column */}\n                <motion.div className="lg:col-span-5 space-y-8">\n'
if old not in text:
    old = '                {/* Settings & Generation Column */}\n                <div className="lg:col-span-5 space-y-8">\n'
text = text.replace(old, "")
p.write_text(text, encoding="utf-8")
print("patched", p)
