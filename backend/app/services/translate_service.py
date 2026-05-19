import logging
import requests
from typing import List, Dict, Any, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from deep_translator import GoogleTranslator
from app.core.config import settings

logger = logging.getLogger(__name__)

class TranslateService:
    def __init__(self, target_lang: str = "vi", service_type: Optional[str] = None):
        self.target_lang = target_lang
        self.service_type = service_type or settings.default_translation_service()  # "google", "nllb", "ollama"
        self.nllb_model = None
        self.nllb_tokenizer = None
        self._nllb_device = "cpu"

    @staticmethod
    def _nllb_lang_code(lang: str) -> str:
        mapping = {
            "ar": "arb_Arab",
            "de": "deu_Latn",
            "en": "eng_Latn",
            "es": "spa_Latn",
            "fr": "fra_Latn",
            "hi": "hin_Deva",
            "id": "ind_Latn",
            "it": "ita_Latn",
            "ja": "jpn_Jpan",
            "ko": "kor_Hang",
            "pt": "por_Latn",
            "ru": "rus_Cyrl",
            "th": "tha_Thai",
            "vi": "vie_Latn",
            "zh": "zho_Hans",
        }
        return mapping.get((lang or "").strip().lower(), "eng_Latn")

    def _load_nllb(self):
        """Lazy load NLLB model."""
        if self.nllb_model is not None:
            return

        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
        from app.core.gpu import resolve_torch_device

        model_name = settings.DEFAULT_NLLB_MODEL
        device = resolve_torch_device() if settings.NLLB_USE_GPU and settings.use_gpu() else "cpu"
        logger.info("Loading NLLB model: %s on %s", model_name, device)
        self.nllb_tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.nllb_model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
        if device == "cuda":
            self.nllb_model = self.nllb_model.cuda()
        self._nllb_device = device

    def translate_text(self, text: str, source_lang: str = "auto") -> str:
        """Translate a single piece of text."""
        if not text.strip():
            return text

        try:
            if self.service_type == "deepl":
                return self._translate_deepl(text, source_lang)

            if self.service_type == "google":
                translated = GoogleTranslator(source=source_lang, target=self.target_lang).translate(text)
                if (
                    translated
                    and source_lang == "auto"
                    and translated.strip() == text.strip()
                    and self.target_lang.split("-")[0].lower() not in text.lower()[:3]
                ):
                    logger.warning(
                        "Google Translate returned unchanged text for target=%s (segment may stay in source language)",
                        self.target_lang,
                    )
                return translated or text
            
            elif self.service_type == "ollama":
                return self._translate_ollama(text)
            
            elif self.service_type == "nllb":
                return self._translate_nllb(text, source_lang)
                
        except Exception as e:
            logger.error(f"Translation error ({self.service_type}): {e}")
            return text
        
        return text

    def _translate_ollama(self, text: str, model: str = "llama3") -> str:
        """Translate using local Ollama instance."""
        url = "http://localhost:11434/api/generate"
        prompt = (
            f"Translate the following text to {self.target_lang}. "
            f"Preserve the tone and style. Output ONLY the translation.\n\n"
            f"Text: {text}"
        )
        payload = {"model": model, "prompt": prompt, "stream": False}
        
        response = requests.post(url, json=payload, timeout=60)
        if response.status_code == 200:
            return response.json().get('response', '').strip().strip('"')
        return text

    def _translate_deepl(self, text: str, source_lang: str) -> str:
        """Translate using DeepL API (highest quality for European languages)."""
        from app.services.deepl_service import DeepLService
        service = DeepLService(target_lang=self.target_lang)
        if not service.is_available():
            logger.warning("DeepL not available (no key or unsupported lang), falling back to Google.")
            return GoogleTranslator(source=source_lang, target=self.target_lang).translate(text) or text
        result = service.translate(text, source_lang)
        return result if result else text

    def _translate_nllb(self, text: str, source_lang: str) -> str:
        """Translate using local NLLB model."""
        self._load_nllb()
        inputs = self.nllb_tokenizer(text, return_tensors="pt")
        if getattr(self, "_nllb_device", "cpu") == "cuda":
            inputs = {k: v.cuda() for k, v in inputs.items()}
        target_lang_code = self._nllb_lang_code(self.target_lang)
        translated_tokens = self.nllb_model.generate(
            **inputs,
            forced_bos_token_id=self.nllb_tokenizer.lang_code_to_id[target_lang_code],
        )
        return self.nllb_tokenizer.batch_decode(translated_tokens, skip_special_tokens=True)[0]

    def translate_batch(
        self,
        segments: List[Dict[str, Any]],
        max_workers: int = 5,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> List[Dict[str, Any]]:
        """Translate a list of segments in parallel."""
        if self.service_type == "nllb":
            max_workers = 1
        logger.info(f"Translating {len(segments)} segments using {self.service_type}")
        
        def translate_item(item):
            idx, seg = item
            original = (seg.get("text") or "").strip()
            try:
                translated = self.translate_text(original)
            except Exception as e:
                logger.warning("Translation failed for segment %d, using original text: %s", idx, e)
                translated = original
            translated = (translated or original).strip()
            return idx, {**seg, 'translated_text': translated, '_untranslated': translated == original}

        results = [None] * len(segments)
        completed = 0
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(translate_item, (i, s)): i for i, s in enumerate(segments)}
            for future in as_completed(futures):
                try:
                    idx, result = future.result()
                    results[idx] = result
                except Exception as e:
                    idx = futures[future]
                    logger.error("Translation future failed for segment %d: %s", idx, e)
                    results[idx] = {**segments[idx], 'translated_text': segments[idx]['text']}
                completed += 1
                if progress_callback:
                    progress_callback(completed, len(segments))
                
        final = [r for r in results if r is not None]
        unchanged = sum(1 for r in final if r.pop("_untranslated", False))
        if final and unchanged == len(final) and self.target_lang.split("-")[0].lower() != "vi":
            logger.error(
                "All %d segments unchanged after translation to '%s' via %s — "
                "output will stay in source language. Check network or switch preset to Hybrid.",
                len(final),
                self.target_lang,
                self.service_type,
            )
        elif unchanged > len(final) * 0.5:
            logger.warning(
                "%d/%d segments unchanged after translation to '%s' via %s",
                unchanged,
                len(final),
                self.target_lang,
                self.service_type,
            )
        return final
