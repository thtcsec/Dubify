"""Edge-TTS voice catalog grouped for Vietnamese / English studio & dubbing."""

from __future__ import annotations

from typing import Any

from app.core.config import settings

# category: vi = Vietnamese specialist, en = English specialist, other = more languages
VOICE_CATALOG: list[dict[str, Any]] = [
    # ── Vietnamese specialists ──
    {"id": "vi-VN-HoaiMyNeural", "name": "Hoài My", "lang": "vi", "gender": "Female", "category": "vi", "accent": "VN", "style": "Tin tức / thuyết minh"},
    {"id": "vi-VN-NamMinhNeural", "name": "Nam Minh", "lang": "vi", "gender": "Male", "category": "vi", "accent": "VN", "style": "Tin tức / trầm ấm"},
    {"id": "en-US-EmmaMultilingualNeural", "name": "Emma (đọc VI)", "lang": "vi", "gender": "Female", "category": "vi", "accent": "Đa ngôn ngữ", "style": "Tự nhiên / podcast"},
    {"id": "en-US-AvaMultilingualNeural", "name": "Ava (đọc VI)", "lang": "vi", "gender": "Female", "category": "vi", "accent": "Đa ngôn ngữ", "style": "Biểu cảm / Shorts"},
    {"id": "en-US-AndrewMultilingualNeural", "name": "Andrew (đọc VI)", "lang": "vi", "gender": "Male", "category": "vi", "accent": "Đa ngôn ngữ", "style": "Trẻ / năng động"},
    {"id": "en-US-BrianMultilingualNeural", "name": "Brian (đọc VI)", "lang": "vi", "gender": "Male", "category": "vi", "accent": "Đa ngôn ngữ", "style": "Thân thiện"},
    {"id": "en-AU-WilliamMultilingualNeural", "name": "William (đọc VI)", "lang": "vi", "gender": "Male", "category": "vi", "accent": "Đa ngôn ngữ", "style": "Trầm / kể chuyện"},
    # ── English specialists (US) ──
    {"id": "en-US-JennyNeural", "name": "Jenny", "lang": "en", "gender": "Female", "category": "en", "accent": "US", "style": "Assistant / friendly"},
    {"id": "en-US-AriaNeural", "name": "Aria", "lang": "en", "gender": "Female", "category": "en", "accent": "US", "style": "News / professional"},
    {"id": "en-US-GuyNeural", "name": "Guy", "lang": "en", "gender": "Male", "category": "en", "accent": "US", "style": "News / documentary"},
    {"id": "en-US-AndrewNeural", "name": "Andrew", "lang": "en", "gender": "Male", "category": "en", "accent": "US", "style": "Casual / young"},
    {"id": "en-US-BrianNeural", "name": "Brian", "lang": "en", "gender": "Male", "category": "en", "accent": "US", "style": "Authoritative"},
    {"id": "en-US-EmmaNeural", "name": "Emma", "lang": "en", "gender": "Female", "category": "en", "accent": "US", "style": "Warm narrator"},
    {"id": "en-US-AvaNeural", "name": "Ava", "lang": "en", "gender": "Female", "category": "en", "accent": "US", "style": "Expressive / ads"},
    {"id": "en-US-ChristopherNeural", "name": "Christopher", "lang": "en", "gender": "Male", "category": "en", "accent": "US", "style": "Calm narrator"},
    {"id": "en-US-EricNeural", "name": "Eric", "lang": "en", "gender": "Male", "category": "en", "accent": "US", "style": "Confident host"},
    {"id": "en-US-MichelleNeural", "name": "Michelle", "lang": "en", "gender": "Female", "category": "en", "accent": "US", "style": "Clear presenter"},
    {"id": "en-US-RogerNeural", "name": "Roger", "lang": "en", "gender": "Male", "category": "en", "accent": "US", "style": "Deep / serious"},
    {"id": "en-US-SteffanNeural", "name": "Steffan", "lang": "en", "gender": "Male", "category": "en", "accent": "US", "style": "Energetic"},
    {"id": "en-US-AnaNeural", "name": "Ana", "lang": "en", "gender": "Female", "category": "en", "accent": "US", "style": "Soft / lifestyle"},
    # ── English specialists (UK / AU / CA / IN) ──
    {"id": "en-GB-SoniaNeural", "name": "Sonia", "lang": "en", "gender": "Female", "category": "en", "accent": "UK", "style": "BBC-style news"},
    {"id": "en-GB-RyanNeural", "name": "Ryan", "lang": "en", "gender": "Male", "category": "en", "accent": "UK", "style": "British narrator"},
    {"id": "en-GB-LibbyNeural", "name": "Libby", "lang": "en", "gender": "Female", "category": "en", "accent": "UK", "style": "Youth / casual UK"},
    {"id": "en-GB-ThomasNeural", "name": "Thomas", "lang": "en", "gender": "Male", "category": "en", "accent": "UK", "style": "Formal UK"},
    {"id": "en-AU-NatashaNeural", "name": "Natasha", "lang": "en", "gender": "Female", "category": "en", "accent": "AU", "style": "Australian host"},
    {"id": "en-AU-WilliamNeural", "name": "William", "lang": "en", "gender": "Male", "category": "en", "accent": "AU", "style": "Australian narrator"},
    {"id": "en-CA-LiamNeural", "name": "Liam", "lang": "en", "gender": "Male", "category": "en", "accent": "CA", "style": "Canadian male"},
    {"id": "en-CA-ClaraNeural", "name": "Clara", "lang": "en", "gender": "Female", "category": "en", "accent": "CA", "style": "Canadian female"},
    {"id": "en-IN-NeerjaNeural", "name": "Neerja", "lang": "en", "gender": "Female", "category": "en", "accent": "IN", "style": "Indian English"},
    {"id": "en-IN-PrabhatNeural", "name": "Prabhat", "lang": "en", "gender": "Male", "category": "en", "accent": "IN", "style": "Indian English male"},
    {"id": "en-IE-ConnorNeural", "name": "Connor", "lang": "en", "gender": "Male", "category": "en", "accent": "IE", "style": "Irish English"},
    {"id": "en-IE-EmilyNeural", "name": "Emily", "lang": "en", "gender": "Female", "category": "en", "accent": "IE", "style": "Irish English female"},
    # ── Other languages ──
    {"id": "ja-JP-NanamiNeural", "name": "Nanami", "lang": "ja", "gender": "Female", "category": "other", "accent": "JP", "style": ""},
    {"id": "ja-JP-KeitaNeural", "name": "Keita", "lang": "ja", "gender": "Male", "category": "other", "accent": "JP", "style": ""},
    {"id": "ko-KR-SunHiNeural", "name": "Sun-Hi", "lang": "ko", "gender": "Female", "category": "other", "accent": "KR", "style": ""},
    {"id": "ko-KR-InJoonNeural", "name": "InJoon", "lang": "ko", "gender": "Male", "category": "other", "accent": "KR", "style": ""},
    {"id": "zh-CN-XiaoxiaoNeural", "name": "Xiaoxiao", "lang": "zh", "gender": "Female", "category": "other", "accent": "CN", "style": ""},
    {"id": "zh-CN-YunxiNeural", "name": "Yunxi", "lang": "zh", "gender": "Male", "category": "other", "accent": "CN", "style": ""},
    {"id": "fr-FR-DeniseNeural", "name": "Denise", "lang": "fr", "gender": "Female", "category": "other", "accent": "FR", "style": ""},
    {"id": "fr-FR-HenriNeural", "name": "Henri", "lang": "fr", "gender": "Male", "category": "other", "accent": "FR", "style": ""},
    {"id": "es-ES-ElviraNeural", "name": "Elvira", "lang": "es", "gender": "Female", "category": "other", "accent": "ES", "style": ""},
    {"id": "es-ES-AlvaroNeural", "name": "Alvaro", "lang": "es", "gender": "Male", "category": "other", "accent": "ES", "style": ""},
    {"id": "de-DE-KatjaNeural", "name": "Katja", "lang": "de", "gender": "Female", "category": "other", "accent": "DE", "style": ""},
    {"id": "de-DE-ConradNeural", "name": "Conrad", "lang": "de", "gender": "Male", "category": "other", "accent": "DE", "style": ""},
    {"id": "pt-BR-FranciscaNeural", "name": "Francisca", "lang": "pt", "gender": "Female", "category": "other", "accent": "BR", "style": ""},
    {"id": "pt-BR-AntonioNeural", "name": "Antonio", "lang": "pt", "gender": "Male", "category": "other", "accent": "BR", "style": ""},
    {"id": "id-ID-GadisNeural", "name": "Gadis", "lang": "id", "gender": "Female", "category": "other", "accent": "ID", "style": ""},
    {"id": "id-ID-ArdiNeural", "name": "Ardi", "lang": "id", "gender": "Male", "category": "other", "accent": "ID", "style": ""},
    {"id": "th-TH-PremwadeeNeural", "name": "Premwadee", "lang": "th", "gender": "Female", "category": "other", "accent": "TH", "style": ""},
    {"id": "th-TH-NiwatNeural", "name": "Niwat", "lang": "th", "gender": "Male", "category": "other", "accent": "TH", "style": ""},
]

VOICE_GROUPS = [
    {"id": "vi", "label": "Tiếng Việt (chuyên)", "label_en": "Vietnamese"},
    {"id": "en", "label": "English (chuyên)", "label_en": "English"},
    {"id": "other", "label": "Ngôn ngữ khác", "label_en": "Other languages"},
]


def voices_payload() -> dict[str, Any]:
    voices = list(VOICE_CATALOG)
    groups = list(VOICE_GROUPS)

    if getattr(settings, "ELEVENLABS_API_KEY", ""):
        groups.insert(0, {"id": "pro", "label": "Pro voices", "label_en": "Pro voices"})
        voices = [
            {"id": "elevenlabs:21m00Tcm4TlvDq8ikWAM", "name": "Rachel (ElevenLabs)", "lang": "multi", "gender": "Female", "category": "pro", "accent": "Multi", "style": "Pro"},
            {"id": "elevenlabs:EXAVITQu4vr4xnSDxMaL", "name": "Bella (ElevenLabs)", "lang": "multi", "gender": "Female", "category": "pro", "accent": "Multi", "style": "Pro"},
            {"id": "elevenlabs:ErXwobaYiN019PkySvjV", "name": "Antoni (ElevenLabs)", "lang": "multi", "gender": "Male", "category": "pro", "accent": "Multi", "style": "Pro"},
        ] + voices

    return {
        "voices": voices,
        "groups": groups,
    }
