"""Celery tasks for all generation job types.

Each task:
  1. Updates Job status to 'running' in DB
  2. Publishes progress to Redis pub/sub (channel: job:{job_id})
  3. Calls the appropriate pipeline
  4. Creates Asset record with output
  5. Updates Job status to 'done' or 'failed'
  6. Handles retries up to max_retries
"""
import json
import os
import traceback
from datetime import datetime, timezone

from loguru import logger

from backend.celery_app import celery_app
from backend.config import get_settings


PRIORITY_MAP = {"high": 9, "medium": 6, "normal": 5, "low": 2}
SETTINGS = get_settings()


def _get_queue(priority: str) -> str:
    return {"high": "high", "medium": "medium", "normal": "default", "low": "low"}.get(
        priority, "default"
    )


def _publish_progress(
    job_id: str,
    progress_pct: int,
    current_step: int,
    total_steps: int,
    status: str = "running",
    eta_seconds: int | None = None,
):
    """Publish job progress to Redis pub/sub for WebSocket streaming.

    Channel: job:{job_id}
    Update interval: every call (tasks should call every 500ms during generation).
    """
    try:
        import redis
        r = redis.Redis.from_url(SETTINGS.REDIS_URL)
        payload = json.dumps({
            "job_id": job_id,
            "progress_pct": progress_pct,
            "current_step": current_step,
            "total_steps": total_steps,
            "eta_seconds": eta_seconds,
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        r.publish(f"job:{job_id}", payload)
    except Exception as e:
        logger.warning(f"Failed to publish progress for job {job_id}: {e}")


def _update_job_status(job_id: str, status: str, **extra_fields):
    """Update job status in database (synchronous, for use in Celery worker)."""
    try:
        from sqlalchemy import create_engine, update
        from sqlalchemy.orm import Session
        from backend.models.job import Job

        # Use synchronous engine for Celery tasks
        sync_url = SETTINGS.DATABASE_URL.replace("+aiosqlite", "").replace("+asyncpg", "+psycopg2")
        engine = create_engine(sync_url)

        with Session(engine) as session:
            values = {"status": status}
            if status == "running":
                values["started_at"] = datetime.now(timezone.utc)
            elif status in ("done", "failed", "cancelled"):
                values["completed_at"] = datetime.now(timezone.utc)
            values.update(extra_fields)

            session.execute(
                update(Job).where(Job.id == job_id).values(**values)
            )
            session.commit()
    except Exception as e:
        logger.error(f"Failed to update job {job_id} status: {e}")


def _create_asset_record(
    job_id: str,
    project_id: str,
    asset_type: str,
    asset_subtype: str,
    storage_path: str,
    mime_type: str,
    file_size_bytes: int,
    width: int | None = None,
    height: int | None = None,
    duration_ms: int | None = None,
) -> str:
    """Create an Asset record in the database. Returns asset ID."""
    import uuid
    try:
        from sqlalchemy import create_engine, insert
        from sqlalchemy.orm import Session
        from backend.models.asset import Asset

        sync_url = SETTINGS.DATABASE_URL.replace("+aiosqlite", "").replace("+asyncpg", "+psycopg2")
        engine = create_engine(sync_url)

        asset_id = str(uuid.uuid4())
        with Session(engine) as session:
            session.execute(
                insert(Asset).values(
                    id=asset_id,
                    project_id=project_id,
                    job_id=job_id,
                    type=asset_type,
                    subtype=asset_subtype,
                    storage_path=storage_path,
                    mime_type=mime_type,
                    file_size_bytes=file_size_bytes,
                    width=width,
                    height=height,
                    duration_ms=duration_ms,
                )
            )
            session.commit()
        return asset_id
    except Exception as e:
        logger.error(f"Failed to create asset record: {e}")
        raise


def _get_output_dir(project_id: str, asset_type: str) -> str:
    """Get output directory for generated assets."""
    subdir = {"image": "images", "video": "video", "audio": "audio"}.get(asset_type, "misc")
    output_dir = os.path.join(SETTINGS.STORAGE_BASE_PATH, "outputs", project_id, subdir)
    os.makedirs(output_dir, exist_ok=True)
    return output_dir


def _get_optimization_params() -> dict:
    """Get hardware-dependent optimization parameters."""
    try:
        from backend.hardware_profile import get_hardware_profile
        strategy = get_hardware_profile()
        return {
            "precision": strategy.precision,
            "use_xformers": strategy.use_xformers,
        }
    except Exception:
        return {"precision": "fp16", "use_xformers": False}


# ---------------------------------------------------------------------------
# Image Generation Task
# ---------------------------------------------------------------------------

@celery_app.task(bind=True, name="tasks.image_generation", max_retries=2)
def image_generation_task(self, job_id: str, params: dict):
    """Image generation — T2I, I2I, inpaint, outpaint.

    params expected keys:
      - project_id, model_path, mode (t2i/i2i/inpaint/outpaint)
      - positive_prompt, negative_prompt, width, height, steps, cfg_scale
      - seed, seed_mode, variation_count, lora_stack
      - source_image_path (for i2i/inpaint), mask_image_path (for inpaint)
      - expand_direction, expand_amount (for outpaint)
      - denoise_strength (for i2i/inpaint)
      - cn_* fields for ControlNet
    """
    logger.info(f"Image generation job {job_id} started", extra={"job_id": job_id})
    _update_job_status(job_id, "running")
    _publish_progress(job_id, 0, 0, params.get("steps", 30), "running")

    try:
        from backend.pipelines.image import get_image_pipeline

        pipeline = get_image_pipeline()
        opt = _get_optimization_params()

        project_id = params["project_id"]
        mode = params.get("mode", "t2i")
        output_dir = _get_output_dir(project_id, "image")
        variation_count = params.get("variation_count", 1)

        asset_ids = []

        for var_idx in range(variation_count):
            def progress_cb(step, total):
                pct = int(step / total * 100)
                _publish_progress(job_id, pct, step, total, "running")
                self.update_state(
                    state="PROGRESS",
                    meta={"progress_pct": pct, "current_step": step, "total_steps": total},
                )

            gen_kwargs = {
                "model_path": params["model_path"],
                "positive_prompt": params["positive_prompt"],
                "negative_prompt": params.get("negative_prompt", ""),
                "width": params.get("width", 512),
                "height": params.get("height", 512),
                "steps": params.get("steps", 30),
                "cfg_scale": params.get("cfg_scale", 7.0),
                "seed": params.get("seed", -1),
                "seed_mode": params.get("seed_mode", "random"),
                "lora_stack": params.get("lora_stack", []),
                "output_dir": output_dir,
                "precision": opt["precision"],
                "use_xformers": opt["use_xformers"],
                "progress_callback": progress_cb,
            }

            # Mode-specific kwargs
            if mode == "t2i":
                gen_kwargs["sampler"] = params.get("sampler")
                gen_kwargs["scheduler"] = params.get("scheduler")
                # ControlNet
                if params.get("cn_enabled"):
                    gen_kwargs["controlnet_path"] = params.get("controlnet_path")
                    gen_kwargs["controlnet_image"] = params.get("controlnet_image")
                    gen_kwargs["controlnet_strength"] = params.get("cn_strength", 1.0)
                result = pipeline.generate_t2i(**gen_kwargs)
            elif mode == "i2i":
                gen_kwargs["source_image_path"] = params["source_image_path"]
                gen_kwargs["denoise_strength"] = params.get("denoise_strength", 0.75)
                result = pipeline.generate_i2i(**gen_kwargs)
            elif mode == "inpaint":
                gen_kwargs["source_image_path"] = params["source_image_path"]
                gen_kwargs["mask_image_path"] = params["mask_image_path"]
                gen_kwargs["denoise_strength"] = params.get("denoise_strength", 1.0)
                result = pipeline.generate_inpaint(**gen_kwargs)
            elif mode == "outpaint":
                gen_kwargs["source_image_path"] = params["source_image_path"]
                gen_kwargs["expand_direction"] = params.get("expand_direction", "right")
                gen_kwargs["expand_amount"] = params.get("expand_amount", 256)
                result = pipeline.generate_outpaint(**gen_kwargs)
            else:
                raise ValueError(f"Unknown image mode: {mode}")

            # Determine subtype
            subtype_map = {"t2i": "still", "i2i": "i2i", "inpaint": "inpaint", "outpaint": "outpaint"}
            asset_subtype = subtype_map.get(mode, "still")

            asset_id = _create_asset_record(
                job_id=job_id,
                project_id=project_id,
                asset_type="image",
                asset_subtype=asset_subtype,
                storage_path=result.output_path,
                mime_type=result.mime_type,
                file_size_bytes=result.file_size_bytes,
                width=result.width,
                height=result.height,
            )
            asset_ids.append(asset_id)

        _update_job_status(job_id, "done", progress_pct=100)
        _publish_progress(job_id, 100, params.get("steps", 30), params.get("steps", 30), "done")

        logger.info(f"Image generation job {job_id} completed, {len(asset_ids)} assets created")
        return {"job_id": job_id, "status": "done", "asset_ids": asset_ids}

    except Exception as e:
        error_msg = str(e)
        error_tb = traceback.format_exc()
        logger.error(f"Image generation job {job_id} failed: {error_msg}\n{error_tb}")

        _update_job_status(
            job_id, "failed",
            error_code="image_generation_error",
            error_msg=error_msg[:1000],
            progress_pct=0,
        )
        _publish_progress(job_id, 0, 0, 0, "failed")

        # Retry if under max_retries
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=30)
        return {"job_id": job_id, "status": "failed", "error": error_msg}


# ---------------------------------------------------------------------------
# Video Generation Task
# ---------------------------------------------------------------------------

@celery_app.task(bind=True, name="tasks.video_generation", max_retries=2)
def video_generation_task(self, job_id: str, params: dict):
    """Video generation — T2V, I2V, V2V."""
    logger.info(f"Video generation job {job_id} started", extra={"job_id": job_id})
    _update_job_status(job_id, "running")
    _publish_progress(job_id, 0, 0, params.get("steps", 30), "running")

    try:
        from backend.pipelines.video import get_video_pipeline

        pipeline = get_video_pipeline()
        opt = _get_optimization_params()

        project_id = params["project_id"]
        output_dir = _get_output_dir(project_id, "video")

        def progress_cb(step, total):
            pct = int(step / total * 100)
            _publish_progress(job_id, pct, step, total, "running")
            self.update_state(
                state="PROGRESS",
                meta={"progress_pct": pct, "current_step": step, "total_steps": total},
            )

        result = pipeline.generate(
            model_path=params["model_path"],
            architecture=params.get("architecture", "ltxv"),
            mode=params.get("mode", "i2v"),
            positive_prompt=params["positive_prompt"],
            negative_prompt=params.get("negative_prompt", ""),
            source_image_path=params.get("source_image_path"),
            source_video_path=params.get("source_video_path"),
            width=params.get("width", 1280),
            height=params.get("height", 720),
            frames=params.get("frames", 49),
            fps=params.get("fps", 24),
            steps=params.get("steps", 30),
            cfg_scale=params.get("cfg_scale", 7.0),
            motion_strength=params.get("motion_strength"),
            seed=params.get("seed", -1),
            lora_stack=params.get("lora_stack", []),
            output_dir=output_dir,
            precision=opt["precision"],
            use_xformers=opt["use_xformers"],
            progress_callback=progress_cb,
        )

        mode = params.get("mode", "i2v")
        subtype_map = {"t2v": "clip", "i2v": "clip", "v2v": "v2v"}
        asset_subtype = subtype_map.get(mode, "clip")

        asset_id = _create_asset_record(
            job_id=job_id,
            project_id=project_id,
            asset_type="video",
            asset_subtype=asset_subtype,
            storage_path=result.output_path,
            mime_type=result.mime_type,
            file_size_bytes=result.file_size_bytes,
            width=result.width,
            height=result.height,
            duration_ms=result.duration_ms,
        )

        _update_job_status(job_id, "done", progress_pct=100)
        _publish_progress(job_id, 100, params.get("steps", 30), params.get("steps", 30), "done")

        logger.info(f"Video generation job {job_id} completed, asset {asset_id}")
        return {"job_id": job_id, "status": "done", "asset_id": asset_id}

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Video generation job {job_id} failed: {error_msg}")
        _update_job_status(job_id, "failed", error_code="video_generation_error", error_msg=error_msg[:1000])
        _publish_progress(job_id, 0, 0, 0, "failed")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=30)
        return {"job_id": job_id, "status": "failed", "error": error_msg}


# ---------------------------------------------------------------------------
# Audio Generation Task
# ---------------------------------------------------------------------------

@celery_app.task(bind=True, name="tasks.audio_generation", max_retries=2)
def audio_generation_task(self, job_id: str, params: dict):
    """Audio generation — music, sfx, tts, lipsync."""
    logger.info(f"Audio generation job {job_id} started", extra={"job_id": job_id})
    _update_job_status(job_id, "running")
    _publish_progress(job_id, 0, 0, 3, "running")

    try:
        from backend.pipelines.audio import get_audio_pipeline

        pipeline = get_audio_pipeline()
        project_id = params["project_id"]
        output_dir = _get_output_dir(project_id, "audio")
        subtype = params.get("subtype", "music")

        def progress_cb(step, total):
            pct = int(step / total * 100)
            _publish_progress(job_id, pct, step, total, "running")
            self.update_state(
                state="PROGRESS",
                meta={"progress_pct": pct, "current_step": step, "total_steps": total},
            )

        if subtype == "music":
            result = pipeline.generate_music(
                prompt=params.get("prompt", ""),
                duration_seconds=params.get("duration_seconds", 10.0),
                model_name=params.get("model_name", "facebook/musicgen-small"),
                output_dir=output_dir,
                progress_callback=progress_cb,
            )
            asset_subtype = "music"
            mime_type = result.mime_type
        elif subtype == "sfx":
            result = pipeline.generate_sfx(
                prompt=params.get("prompt", ""),
                duration_seconds=params.get("duration_seconds", 5.0),
                model_name=params.get("model_name", "facebook/audiogen-medium"),
                output_dir=output_dir,
                progress_callback=progress_cb,
            )
            asset_subtype = "sfx"
            mime_type = result.mime_type
        elif subtype == "tts":
            result = pipeline.generate_tts(
                text=params.get("prompt", ""),
                model_name=params.get("model_name", "tts_models/en/ljspeech/tacotron2-DDC"),
                speaker=params.get("speaker"),
                language=params.get("language"),
                output_dir=output_dir,
                progress_callback=progress_cb,
            )
            asset_subtype = "tts"
            mime_type = result.mime_type
        elif subtype == "lipsync":
            lip_result = pipeline.generate_lipsync(
                audio_path=params["audio_path"],
                video_path=params["video_path"],
                output_dir=output_dir,
                wav2lip_checkpoint=params.get("wav2lip_checkpoint", "wav2lip_gan.pth"),
                progress_callback=progress_cb,
            )
            asset_id = _create_asset_record(
                job_id=job_id,
                project_id=project_id,
                asset_type="video",
                asset_subtype="lipsync",
                storage_path=lip_result.output_path,
                mime_type=lip_result.mime_type,
                file_size_bytes=lip_result.file_size_bytes,
                duration_ms=lip_result.duration_ms,
            )
            _update_job_status(job_id, "done", progress_pct=100)
            _publish_progress(job_id, 100, 4, 4, "done")
            return {"job_id": job_id, "status": "done", "asset_id": asset_id}
        else:
            raise ValueError(f"Unknown audio subtype: {subtype}")

        asset_id = _create_asset_record(
            job_id=job_id,
            project_id=project_id,
            asset_type="audio",
            asset_subtype=asset_subtype,
            storage_path=result.output_path,
            mime_type=mime_type,
            file_size_bytes=result.file_size_bytes,
            duration_ms=result.duration_ms,
        )

        _update_job_status(job_id, "done", progress_pct=100)
        _publish_progress(job_id, 100, 3, 3, "done")

        logger.info(f"Audio generation job {job_id} completed, asset {asset_id}")
        return {"job_id": job_id, "status": "done", "asset_id": asset_id}

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Audio generation job {job_id} failed: {error_msg}")
        _update_job_status(job_id, "failed", error_code="audio_generation_error", error_msg=error_msg[:1000])
        _publish_progress(job_id, 0, 0, 0, "failed")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=30)
        return {"job_id": job_id, "status": "failed", "error": error_msg}


# ---------------------------------------------------------------------------
# Interpolation Task (RIFE)
# ---------------------------------------------------------------------------

@celery_app.task(bind=True, name="tasks.interpolation", max_retries=2)
def interpolation_task(self, job_id: str, params: dict):
    """RIFE frame interpolation."""
    logger.info(f"Interpolation job {job_id} started", extra={"job_id": job_id})
    _update_job_status(job_id, "running")
    _publish_progress(job_id, 0, 0, 100, "running")

    try:
        from backend.pipelines.interpolation import get_rife_pipeline

        pipeline = get_rife_pipeline()
        project_id = params["project_id"]
        output_dir = _get_output_dir(project_id, "video")

        multiplier_str = params.get("rife_multiplier", "2x")
        multiplier = int(multiplier_str.replace("x", ""))

        def progress_cb(current, total):
            pct = int(current / total * 100) if total > 0 else 0
            _publish_progress(job_id, pct, int(current), int(total), "running")
            self.update_state(
                state="PROGRESS",
                meta={"progress_pct": pct, "current_step": int(current), "total_steps": int(total)},
            )

        result = pipeline.interpolate(
            input_video_path=params["input_video_path"],
            multiplier=multiplier,
            scene_cut_detect=params.get("scene_cut_detect", True),
            output_dir=output_dir,
            fps=params.get("fps", 24),
            progress_callback=progress_cb,
        )

        asset_id = _create_asset_record(
            job_id=job_id,
            project_id=project_id,
            asset_type="video",
            asset_subtype="interpolated",
            storage_path=result.output_path,
            mime_type=result.mime_type,
            file_size_bytes=result.file_size_bytes,
            duration_ms=result.duration_ms,
        )

        _update_job_status(job_id, "done", progress_pct=100)
        _publish_progress(job_id, 100, 100, 100, "done")

        logger.info(f"Interpolation job {job_id} completed, asset {asset_id}")
        return {"job_id": job_id, "status": "done", "asset_id": asset_id}

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Interpolation job {job_id} failed: {error_msg}")
        _update_job_status(job_id, "failed", error_code="interpolation_error", error_msg=error_msg[:1000])
        _publish_progress(job_id, 0, 0, 0, "failed")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=30)
        return {"job_id": job_id, "status": "failed", "error": error_msg}


# ---------------------------------------------------------------------------
# Render Task (FFmpeg)
# ---------------------------------------------------------------------------

@celery_app.task(bind=True, name="tasks.render", max_retries=2)
def render_task(self, job_id: str, params: dict):
    """Render — FFmpeg timeline assembly.

    Assembles all video clips and mixes audio tracks.
    """
    import subprocess

    logger.info(f"Render job {job_id} started", extra={"job_id": job_id})
    _update_job_status(job_id, "running")
    _publish_progress(job_id, 0, 0, 100, "running")

    try:
        project_id = params["project_id"]
        output_dir = os.path.join(
            SETTINGS.STORAGE_BASE_PATH, "outputs", project_id, "exports"
        )
        os.makedirs(output_dir, exist_ok=True)

        video_clips = params.get("video_clips", [])
        audio_clips = params.get("audio_clips", [])
        resolution = params.get("resolution", "1280x720")
        fps = params.get("fps", 24)
        codec = params.get("codec", "libx264")
        bitrate = params.get("bitrate", "8M")
        audio_codec = params.get("audio_codec", "aac")

        import uuid
        filename = f"render_{uuid.uuid4().hex[:12]}.mp4"
        output_path = os.path.join(output_dir, filename)

        _publish_progress(job_id, 10, 10, 100, "running")

        # Build FFmpeg concat filter for video clips
        if video_clips:
            # Create concat file for video clips
            concat_path = os.path.join(output_dir, f"_concat_{job_id}.txt")
            with open(concat_path, "w") as f:
                for clip in video_clips:
                    clip_path = clip.get("asset_path", "")
                    if clip_path and os.path.exists(clip_path):
                        f.write(f"file '{clip_path}'\n")

            cmd = [
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0", "-i", concat_path,
            ]

            # Add audio if available
            for i, ac in enumerate(audio_clips):
                audio_path = ac.get("asset_path", "")
                if audio_path and os.path.exists(audio_path):
                    cmd.extend(["-i", audio_path])

            width, height = resolution.split("x")
            cmd.extend([
                "-vf", f"scale={width}:{height}",
                "-c:v", codec,
                "-b:v", bitrate,
                "-r", str(fps),
                "-c:a", audio_codec,
                "-pix_fmt", "yuv420p",
                output_path,
            ])

            _publish_progress(job_id, 30, 30, 100, "running")

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
            if result.returncode != 0:
                raise RuntimeError(f"FFmpeg render failed: {result.stderr[:500]}")

            # Cleanup concat file
            try:
                os.remove(concat_path)
            except Exception:
                pass
        else:
            # No video clips — create empty file
            raise ValueError("No video clips provided for render")

        _publish_progress(job_id, 90, 90, 100, "running")

        file_size = os.path.getsize(output_path)

        # Get duration
        try:
            probe = subprocess.run(
                ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", output_path],
                capture_output=True, text=True,
            )
            duration_ms = int(float(probe.stdout.strip()) * 1000)
        except Exception:
            duration_ms = 0

        w, h = resolution.split("x")
        asset_id = _create_asset_record(
            job_id=job_id,
            project_id=project_id,
            asset_type="video",
            asset_subtype="export",
            storage_path=output_path,
            mime_type="video/mp4",
            file_size_bytes=file_size,
            width=int(w),
            height=int(h),
            duration_ms=duration_ms,
        )

        _update_job_status(job_id, "done", progress_pct=100)
        _publish_progress(job_id, 100, 100, 100, "done")

        logger.info(f"Render job {job_id} completed, asset {asset_id}")
        return {"job_id": job_id, "status": "done", "asset_id": asset_id}

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Render job {job_id} failed: {error_msg}")
        _update_job_status(job_id, "failed", error_code="render_error", error_msg=error_msg[:1000])
        _publish_progress(job_id, 0, 0, 0, "failed")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=30)
        return {"job_id": job_id, "status": "failed", "error": error_msg}


# ---------------------------------------------------------------------------
# Export Task
# ---------------------------------------------------------------------------

@celery_app.task(bind=True, name="tasks.export", max_retries=2)
def export_task(self, job_id: str, params: dict):
    """Export — final encode with specified format, resolution, bitrate."""
    import subprocess

    logger.info(f"Export job {job_id} started", extra={"job_id": job_id})
    _update_job_status(job_id, "running")
    _publish_progress(job_id, 0, 0, 100, "running")

    try:
        project_id = params["project_id"]
        source_path = params["source_path"]
        output_format = params.get("format", "mp4")
        resolution = params.get("resolution", "1920x1080")
        fps = params.get("fps", 24)
        codec = params.get("codec", "libx264")
        bitrate = params.get("bitrate", "8M")
        audio_codec = params.get("audio_codec", "aac")

        output_dir = os.path.join(
            SETTINGS.STORAGE_BASE_PATH, "outputs", project_id, "exports"
        )
        os.makedirs(output_dir, exist_ok=True)

        import uuid
        filename = f"export_{uuid.uuid4().hex[:12]}.{output_format}"
        output_path = os.path.join(output_dir, filename)

        _publish_progress(job_id, 20, 20, 100, "running")

        width, height = resolution.split("x")
        cmd = [
            "ffmpeg", "-y",
            "-i", source_path,
            "-vf", f"scale={width}:{height}",
            "-c:v", codec,
            "-b:v", bitrate,
            "-r", str(fps),
            "-c:a", audio_codec,
            "-ar", "48000",
            "-ac", "2",
            "-pix_fmt", "yuv420p",
            output_path,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg export failed: {result.stderr[:500]}")

        _publish_progress(job_id, 90, 90, 100, "running")

        file_size = os.path.getsize(output_path)

        try:
            probe = subprocess.run(
                ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", output_path],
                capture_output=True, text=True,
            )
            duration_ms = int(float(probe.stdout.strip()) * 1000)
        except Exception:
            duration_ms = 0

        mime_map = {"mp4": "video/mp4", "mkv": "video/x-matroska", "webm": "video/webm"}

        asset_id = _create_asset_record(
            job_id=job_id,
            project_id=project_id,
            asset_type="video",
            asset_subtype="export",
            storage_path=output_path,
            mime_type=mime_map.get(output_format, "video/mp4"),
            file_size_bytes=file_size,
            width=int(width),
            height=int(height),
            duration_ms=duration_ms,
        )

        _update_job_status(job_id, "done", progress_pct=100)
        _publish_progress(job_id, 100, 100, 100, "done")

        logger.info(f"Export job {job_id} completed, asset {asset_id}")
        return {"job_id": job_id, "status": "done", "asset_id": asset_id}

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Export job {job_id} failed: {error_msg}")
        _update_job_status(job_id, "failed", error_code="export_error", error_msg=error_msg[:1000])
        _publish_progress(job_id, 0, 0, 0, "failed")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=30)
        return {"job_id": job_id, "status": "failed", "error": error_msg}


# Task registry for dispatching by job type
TASK_REGISTRY = {
    "image_generation": "tasks.image_generation",
    "video_generation": "tasks.video_generation",
    "audio_generation": "tasks.audio_generation",
    "interpolation": "tasks.interpolation",
    "inpaint": "tasks.image_generation",
    "outpaint": "tasks.image_generation",
    "render": "tasks.render",
    "export": "tasks.export",
}
