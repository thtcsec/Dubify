from pathlib import Path

m = "motion"
path = Path(r"d:\tu_projects\Dubify\frontend\src\components\AppSidebar.tsx")
text = path.read_text(encoding="utf-8")
text = text.replace("<" + m + ".div", "<div")
text = text.replace("</" + m + ".motion.div>", "</motion.div>")
path.write_text(text, encoding="utf-8")
print("done")
