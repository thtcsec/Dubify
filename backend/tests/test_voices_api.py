from app.api.voice_catalog import voices_payload


def test_voices_payload_shape():
    payload = voices_payload()
    assert isinstance(payload["voices"], list)
    assert len(payload["voices"]) > 10
    assert isinstance(payload["groups"], list)
    first = payload["voices"][0]
    assert "id" in first and "lang" in first
