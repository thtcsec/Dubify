import logging
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from app.core.config import settings

# Attempt to import faster-whisper. Fallback to standard whisper if needed.
try:
    from faster_whisper import WhisperModel
    HAS_FASTER_WHISPER = True
except ImportError:
    HAS_FASTER_WHISPER = False
    import whisper

logger = logging.getLogger(__name__)

class ASRService:
    def __init__(self, model_size: str = "base", device: Optional[str] = None):
        import torch
        self.model_size = model_size
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model = None

    def _load_model(self):
        if self.model is not None:
            return
        
        logger.info(f"Loading Whisper model: {self.model_size} on {self.device}")
        if HAS_FASTER_WHISPER:
            # compute_type can be float16, int8_float16, int8
            compute_type = "float16" if self.device == "cuda" else "int8"
            self.model = WhisperModel(self.model_size, device=self.device, compute_type=compute_type)
        else:
            self.model = whisper.load_model(self.model_size, device=self.device)

    def transcribe(self, audio_path: Path) -> List[Dict[str, Any]]:
        """Transcribe audio file and return segments with timestamps."""
        self._load_model()
        logger.info(f"Starting transcription for {audio_path}")
        
        segments_out = []
        
        if HAS_FASTER_WHISPER:
            segments, info = self.model.transcribe(str(audio_path), beam_size=5)
            for segment in segments:
                segments_out.append({
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text.strip()
                })
        else:
            result = self.model.transcribe(str(audio_path))
            for segment in result['segments']:
                segments_out.append({
                    "start": segment['start'],
                    "end": segment['end'],
                    "text": segment['text'].strip()
                })
        
        logger.info(f"Transcription completed. Found {len(segments_out)} segments.")
        return segments_out

    @staticmethod
    def merge_segments_by_sentence(segments: List[Dict[str, Any]], max_duration: float = 10.0) -> List[Dict[str, Any]]:
        """
        Merge short segments into sentences to improve translation context.
        Logic adapted from AutoDub.
        """
        import re
        sentence_endings = re.compile(r'[.!?;:]\s*$')
        merged = []
        current_group = {'text': '', 'start': None, 'end': None}

        for i, seg in enumerate(segments):
            text = seg['text'].strip()
            if not text:
                continue

            if current_group['start'] is None:
                current_group['start'] = seg['start']

            if current_group['text']:
                current_group['text'] += ' ' + text
            else:
                current_group['text'] = text

            current_group['end'] = seg['end']

            duration = current_group['end'] - current_group['start']
            has_sentence_end = sentence_endings.search(text)
            
            # Check for significant pause between segments
            has_pause = False
            if i + 1 < len(segments):
                next_start = segments[i + 1]['start']
                pause_duration = next_start - seg['end']
                has_pause = pause_duration > 0.8 # threshold for break

            if has_sentence_end or duration >= max_duration or has_pause:
                merged.append({
                    'text': current_group['text'].strip(),
                    'start': current_group['start'],
                    'end': current_group['end']
                })
                current_group = {'text': '', 'start': None, 'end': None}

        if current_group['text']:
            merged.append({
                'text': current_group['text'].strip(),
                'start': current_group['start'],
                'end': current_group['end']
            })

        return merged

    @staticmethod
    def save_transcript(segments: List[Dict[str, Any]], output_path: Path):
        """Save segments to a JSON file."""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(segments, f, indent=2, ensure_ascii=False)
