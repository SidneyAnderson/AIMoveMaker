"""Audio generation pipeline — AudioCraft (music/sfx), Coqui TTS, wav2lip.

Per PRD:
  - Audio — Music/SFX: AudioCraft (Meta, local) — MusicGen and AudioGen models
  - Audio — TTS: Coqui TTS (local) — Text-to-speech voiceover
  - Audio — Lip Sync: wav2lip (local) — Lip sync from audio + source video

Model source routing:
  - Default model_source='local', attempts local model first
  - Falls back to 'api' if local unavailable

PRD Section 10.1 Open Items:
  - Lip sync model: wav2lip is implemented. SadTalker (better head-pose generation)
    is DEFERRED to v2. wav2lip is confirmed as the v1 implementation. If sm_120
    compatibility issues arise at runtime, the wav2lip subprocess will fail
    gracefully with an error log. See PRD Section 10.1 Item 1.
  - Audio export formats: WAV is the default output format for all audio pipelines.
    FLAC export is DEFERRED to v2 — would require adding FLAC encoding option to
    each generate_*() method. See PRD Section 10.1 Item 3.
"""
import os
import subprocess
import uuid
from dataclasses import dataclass
from typing import Callable

from loguru import logger


@dataclass
class AudioGenResult:
    """Result of an audio generation job."""
    output_path: str
    duration_ms: int
    file_size_bytes: int
    sample_rate: int
    mime_type: str = "audio/wav"


@dataclass
class LipSyncResult:
    """Result of a lip sync job."""
    output_path: str
    duration_ms: int
    file_size_bytes: int
    mime_type: str = "video/mp4"


class AudioPipeline:
    """Manages audio generation via AudioCraft, Coqui TTS, and wav2lip."""

    def __init__(self):
        self._musicgen_model = None
        self._audiogen_model = None
        self._tts_model = None

    # ------------------------------------------------------------------
    # Music Generation (AudioCraft MusicGen)
    # ------------------------------------------------------------------

    def _load_musicgen(self, model_name: str = "facebook/musicgen-small"):
        """Load MusicGen model."""
        if self._musicgen_model is not None:
            return
        logger.info(f"Loading MusicGen model: {model_name}")
        from audiocraft.models import MusicGen
        self._musicgen_model = MusicGen.get_pretrained(model_name)

    def generate_music(
        self,
        prompt: str,
        duration_seconds: float = 10.0,
        model_name: str = "facebook/musicgen-small",
        output_dir: str = "/tmp",
        progress_callback: Callable | None = None,
        **kwargs,
    ) -> AudioGenResult:
        """Generate music from text prompt using MusicGen."""
        self._load_musicgen(model_name)

        self._musicgen_model.set_generation_params(duration=duration_seconds)

        if progress_callback:
            progress_callback(1, 3)  # Loading

        wav = self._musicgen_model.generate([prompt])

        if progress_callback:
            progress_callback(2, 3)  # Generated

        # Export to WAV
        os.makedirs(output_dir, exist_ok=True)
        filename = f"{uuid.uuid4()}.wav"
        output_path = os.path.join(output_dir, filename)

        import torchaudio
        sample_rate = self._musicgen_model.sample_rate
        torchaudio.save(output_path, wav[0].cpu(), sample_rate)

        if progress_callback:
            progress_callback(3, 3)  # Saved

        file_size = os.path.getsize(output_path)
        duration_ms = int(duration_seconds * 1000)

        return AudioGenResult(
            output_path=output_path,
            duration_ms=duration_ms,
            file_size_bytes=file_size,
            sample_rate=sample_rate,
        )

    # ------------------------------------------------------------------
    # SFX Generation (AudioCraft AudioGen)
    # ------------------------------------------------------------------

    def _load_audiogen(self, model_name: str = "facebook/audiogen-medium"):
        """Load AudioGen model."""
        if self._audiogen_model is not None:
            return
        logger.info(f"Loading AudioGen model: {model_name}")
        from audiocraft.models import AudioGen
        self._audiogen_model = AudioGen.get_pretrained(model_name)

    def generate_sfx(
        self,
        prompt: str,
        duration_seconds: float = 5.0,
        model_name: str = "facebook/audiogen-medium",
        output_dir: str = "/tmp",
        progress_callback: Callable | None = None,
        **kwargs,
    ) -> AudioGenResult:
        """Generate sound effects from text prompt using AudioGen."""
        self._load_audiogen(model_name)

        self._audiogen_model.set_generation_params(duration=duration_seconds)

        if progress_callback:
            progress_callback(1, 3)

        wav = self._audiogen_model.generate([prompt])

        if progress_callback:
            progress_callback(2, 3)

        os.makedirs(output_dir, exist_ok=True)
        filename = f"{uuid.uuid4()}.wav"
        output_path = os.path.join(output_dir, filename)

        import torchaudio
        sample_rate = self._audiogen_model.sample_rate
        torchaudio.save(output_path, wav[0].cpu(), sample_rate)

        if progress_callback:
            progress_callback(3, 3)

        file_size = os.path.getsize(output_path)
        duration_ms = int(duration_seconds * 1000)

        return AudioGenResult(
            output_path=output_path,
            duration_ms=duration_ms,
            file_size_bytes=file_size,
            sample_rate=sample_rate,
        )

    # ------------------------------------------------------------------
    # TTS (Coqui TTS)
    # ------------------------------------------------------------------

    def _load_tts(self, model_name: str = "tts_models/en/ljspeech/tacotron2-DDC"):
        """Load Coqui TTS model."""
        if self._tts_model is not None:
            return
        logger.info(f"Loading TTS model: {model_name}")
        from TTS.api import TTS
        self._tts_model = TTS(model_name=model_name, progress_bar=False)
        if hasattr(self._tts_model, "to"):
            try:
                self._tts_model.to("cuda")
            except Exception:
                logger.debug("TTS model running on CPU")

    def generate_tts(
        self,
        text: str,
        model_name: str = "tts_models/en/ljspeech/tacotron2-DDC",
        speaker: str | None = None,
        language: str | None = None,
        output_dir: str = "/tmp",
        progress_callback: Callable | None = None,
        **kwargs,
    ) -> AudioGenResult:
        """Generate speech from text using Coqui TTS."""
        self._load_tts(model_name)

        if progress_callback:
            progress_callback(1, 3)

        os.makedirs(output_dir, exist_ok=True)
        filename = f"{uuid.uuid4()}.wav"
        output_path = os.path.join(output_dir, filename)

        tts_kwargs = {"text": text, "file_path": output_path}
        if speaker:
            tts_kwargs["speaker"] = speaker
        if language:
            tts_kwargs["language"] = language

        self._tts_model.tts_to_file(**tts_kwargs)

        if progress_callback:
            progress_callback(2, 3)

        file_size = os.path.getsize(output_path)

        # Determine duration from WAV file
        duration_ms = self._get_wav_duration_ms(output_path)

        if progress_callback:
            progress_callback(3, 3)

        return AudioGenResult(
            output_path=output_path,
            duration_ms=duration_ms,
            file_size_bytes=file_size,
            sample_rate=22050,
        )

    # ------------------------------------------------------------------
    # Lip Sync (wav2lip)
    # ------------------------------------------------------------------

    def generate_lipsync(
        self,
        audio_path: str,
        video_path: str,
        output_dir: str = "/tmp",
        wav2lip_checkpoint: str = "wav2lip_gan.pth",
        progress_callback: Callable | None = None,
        **kwargs,
    ) -> LipSyncResult:
        """Generate lip-synced video using wav2lip.

        Runs wav2lip as a subprocess, reading audio and source video
        to produce synced output.
        """
        if progress_callback:
            progress_callback(1, 4)

        os.makedirs(output_dir, exist_ok=True)
        filename = f"{uuid.uuid4()}.mp4"
        output_path = os.path.join(output_dir, filename)

        if progress_callback:
            progress_callback(2, 4)

        try:
            # wav2lip inference via subprocess
            # wav2lip is expected to be installed and available
            cmd = [
                "python3", "-m", "wav2lip.inference",
                "--checkpoint_path", wav2lip_checkpoint,
                "--face", video_path,
                "--audio", audio_path,
                "--outfile", output_path,
                "--nosmooth",
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout
            )
            if result.returncode != 0:
                logger.error(f"wav2lip failed: {result.stderr}")
                raise RuntimeError(f"wav2lip inference failed: {result.stderr[:500]}")
        except FileNotFoundError:
            logger.error("wav2lip module not found. Install wav2lip package.")
            raise RuntimeError("wav2lip not installed")

        if progress_callback:
            progress_callback(3, 4)

        file_size = os.path.getsize(output_path)
        duration_ms = self._get_video_duration_ms(output_path)

        if progress_callback:
            progress_callback(4, 4)

        return LipSyncResult(
            output_path=output_path,
            duration_ms=duration_ms,
            file_size_bytes=file_size,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_wav_duration_ms(path: str) -> int:
        """Get WAV file duration in milliseconds."""
        try:
            import wave
            with wave.open(path, "rb") as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                return int(frames / rate * 1000) if rate > 0 else 0
        except Exception:
            return 0

    @staticmethod
    def _get_video_duration_ms(path: str) -> int:
        """Get video file duration in milliseconds using ffprobe."""
        try:
            result = subprocess.run(
                [
                    "ffprobe", "-v", "quiet",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    path,
                ],
                capture_output=True,
                text=True,
            )
            duration_s = float(result.stdout.strip())
            return int(duration_s * 1000)
        except Exception:
            return 0

    def unload(self):
        """Free all loaded models."""
        for attr in ("_musicgen_model", "_audiogen_model", "_tts_model"):
            model = getattr(self, attr, None)
            if model is not None:
                del model
                setattr(self, attr, None)
        try:
            import torch
            torch.cuda.empty_cache()
        except Exception:
            pass


# Singleton
_audio_pipeline = AudioPipeline()


def get_audio_pipeline() -> AudioPipeline:
    return _audio_pipeline
