/**
 * Client-side mirror of backend/errors.py catalog (gap #11).
 * Provides user-friendly titles, messages, and suggested actions for job errors.
 * Used across Timeline, Storyboard, Settings, etc.
 */

export interface ErrorInfo {
  code: string;
  title: string;
  userMessage: string;
  suggestedAction: string;
  severity: 'error' | 'warning';
}

const CATALOG: Record<string, ErrorInfo> = {
  image_generation_error: {
    code: 'image_generation_error',
    title: 'Image Generation Failed',
    userMessage: 'The diffusion model failed to generate the image. This can happen with very complex prompts, unusual seeds, or temporary model loading issues.',
    suggestedAction: 'Try a simpler prompt, lower resolution, different seed, or retry the job.',
    severity: 'error',
  },
  video_generation_error: {
    code: 'video_generation_error',
    title: 'Video Generation Failed',
    userMessage: 'Video model (LTX / WAN) encountered an error. Common causes: high VRAM usage, long duration, or model-specific prompt issues.',
    suggestedAction: 'Reduce frame count or resolution, remove heavy LoRAs/ControlNet, or try a different model.',
    severity: 'error',
  },
  audio_generation_error: {
    code: 'audio_generation_error',
    title: 'Audio Generation Failed',
    userMessage: 'MusicGen, AudioGen, or TTS pipeline failed. This often relates to prompt length or resource contention.',
    suggestedAction: 'Shorten the prompt or split into multiple clips and retry.',
    severity: 'error',
  },
  interpolation_error: {
    code: 'interpolation_error',
    title: 'Frame Interpolation Failed',
    userMessage: 'RIFE interpolation could not process the video.',
    suggestedAction: 'Ensure the source has enough frames and try again.',
    severity: 'error',
  },
  render_error: {
    code: 'render_error',
    title: 'Timeline Render Failed',
    userMessage: 'FFmpeg render of the final timeline failed. Possible causes: missing assets or incompatible clip formats.',
    suggestedAction: 'Verify all assets in the timeline still exist and retry.',
    severity: 'error',
  },
  export_error: {
    code: 'export_error',
    title: 'Export Job Failed',
    userMessage: 'The export (PNG sequence or other) could not complete.',
    suggestedAction: 'Verify input clips are valid and try a smaller export.',
    severity: 'error',
  },
  oom_error: {
    code: 'oom_error',
    title: 'Out of Memory (VRAM)',
    userMessage: 'The job exceeded available GPU memory.',
    suggestedAction: 'Lower resolution, reduce frames/LoRAs, or route via Vast.ai.',
    severity: 'error',
  },
};

export function getErrorInfo(code: string | null | undefined, rawMsg?: string | null): ErrorInfo {
  if (!code) {
    return {
      code: 'unknown_error',
      title: 'Unknown Error',
      userMessage: rawMsg || 'An unexpected error occurred during processing.',
      suggestedAction: 'Retry the job. Check the detailed logs if the problem persists.',
      severity: 'error',
    };
  }
  const entry = CATALOG[code];
  if (!entry) {
    return {
      code,
      title: code.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
      userMessage: rawMsg || 'An error occurred.',
      suggestedAction: 'Retry the job or check the logs for more details.',
      severity: 'error',
    };
  }
  return { ...entry };
}

export const ALL_ERROR_CODES = Object.keys(CATALOG);
