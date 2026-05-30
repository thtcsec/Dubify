import json

from app.services.research_video_service import _escape_json_control_chars, _parse_research_json


def test_escape_json_control_chars_multiline_script():
    raw = """{
  "research_summary": "ok",
  "confidence": "high",
  "sources": [],
  "script": "[Hook] Line one
[STAT: 42%]
Line two"
}"""
    fixed = _escape_json_control_chars(raw)
    data = json.loads(fixed)
    assert "[STAT: 42%]" in data["script"]
    assert "\n" in data["script"]


def test_parse_research_json_with_raw_newlines():
    raw = """```json
{
  "research_summary": "Brief",
  "confidence": "medium",
  "sources": [{"title": "A", "url": "", "snippet": "x"}],
  "script": "[Hook] Intro
[STAT: 10M users]
[DEF: Term — meaning]"
}
```"""
    data = _parse_research_json(raw)
    assert data["confidence"] == "medium"
    assert "[STAT: 10M users]" in data["script"]
