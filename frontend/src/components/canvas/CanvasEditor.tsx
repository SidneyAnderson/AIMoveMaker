import React, { useState, useRef, useEffect } from 'react'
import { X, Trash2, RefreshCw, Wand2, Download, Loader2, AlertCircle } from 'lucide-react'
import { getErrorInfo } from '@/lib/errorCatalog'
import MaskCanvas from './MaskCanvas'
import { loadAssetImage, uploadAsset } from '@/api/assets'
import { createJob } from '@/api/jobs'
import { useJobStore } from '@/stores/jobStore'
import { toast } from 'sonner'
import { createTemplate } from '@/api/prompts'

interface CanvasEditorProps {
  projectId: string
  keyframeId: string
  assetId: string | null
  initialPrompt?: string
  onClose: () => void
  onAssetUpdated?: (newAssetId: string) => void
}

export default function CanvasEditor({
  projectId,
  keyframeId,
  assetId,
  initialPrompt = '',
  onClose,
  onAssetUpdated,
}: CanvasEditorProps) {
  const [baseImage, setBaseImage] = useState<HTMLImageElement | null>(null)
  const [brushSize, setBrushSize] = useState(28)
  const [maskDataUrl, setMaskDataUrl] = useState<string | null>(null)
  const [prompt, setPrompt] = useState(initialPrompt)
  const [isLoadingImage, setIsLoadingImage] = useState(true)

  // Outpaint controls (Phase 2)
  const [expandDirection, setExpandDirection] = useState<'right' | 'left' | 'top' | 'bottom'>('right')
  const [expandAmount, setExpandAmount] = useState(256)

  // Adjustments (B/C/S) - live preview + apply (Phase 3 polish)
  const [adjBrightness, setAdjBrightness] = useState(1.0)
  const [adjContrast, setAdjContrast] = useState(1.0)
  const [adjSaturation, setAdjSaturation] = useState(1.0)

  const adjustmentFilter = `brightness(${adjBrightness}) contrast(${adjContrast}) saturate(${adjSaturation})`

  // Rectangular crop (full implementation)
  const [isCropping, setIsCropping] = useState(false)
  const [cropRect, setCropRect] = useState<{ x: number; y: number; width: number; height: number } | null>(null)
  const [cropAspect, setCropAspect] = useState<number | null>(null) // e.g. 16/9, 4/3, 1, null = free
  const cropStartRef = useRef<{ x: number; y: number } | null>(null)

  // History for undo (stores previous base image as data URLs)
  const [history, setHistory] = useState<string[]>([])

  // Job progress tracking (Phase 3 polish)
  const [activeJobId, setActiveJobId] = useState<string | null>(null)
  const activeJobs = useJobStore((s) => s.activeJobs)
  const currentJobProgress = activeJobId ? activeJobs[activeJobId] : null

  const generationInProgress = !!activeJobId
  const generationProgress = currentJobProgress?.progressPct ?? 0
  const generationStatus = currentJobProgress?.status ?? 'running'
  const generationEta = currentJobProgress?.etaSeconds

  // Keyboard shortcuts
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose()
      }
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'z') {
        e.preventDefault()
        if (e.shiftKey) {
          // future: redo
        } else {
          handleUndo()
        }
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const [maskKey, setMaskKey] = useState(0)

  // Load the source asset image when assetId changes
  useEffect(() => {
    let cancelled = false
    if (!assetId) {
      setBaseImage(null)
      setIsLoadingImage(false)
      return
    }

    setIsLoadingImage(true)
    loadAssetImage(projectId, assetId)
      .then((img) => {
        if (!cancelled) {
          setBaseImage(img)
          setIsLoadingImage(false)
        }
      })
      .catch((err) => {
        console.error('Failed to load asset image for Canvas', err)
        if (!cancelled) {
          toast.error('Failed to load image')
          setIsLoadingImage(false)
        }
      })

    return () => {
      cancelled = true
    }
  }, [projectId, assetId])

  const handleMaskChange = (dataUrl: string | null) => {
    setMaskDataUrl(dataUrl)
  }

  const handleClearMask = () => {
    setMaskDataUrl(null)
    setMaskKey(k => k + 1) // force remount of canvas to clear drawing
  }

  const handleInvertMask = () => {
    // Simple invert: we can't easily invert the internal canvas without ref,
    // so for now just clear (full invert can be added later)
    setMaskDataUrl(null)
    setMaskKey(k => k + 1)
    toast.info('Mask cleared (full invert coming in polish)')
  }

  const pushHistory = async () => {
    if (baseImage) {
      const canvas = document.createElement('canvas')
      canvas.width = baseImage.width
      canvas.height = baseImage.height
      canvas.getContext('2d')!.drawImage(baseImage, 0, 0)
      const dataUrl = canvas.toDataURL('image/png')
      setHistory((h) => [...h.slice(-19), dataUrl]) // keep last ~20
    }
  }

  const handleUndo = async () => {
    if (history.length === 0) return
    const prev = history[history.length - 1]
    const img = await new Promise<HTMLImageElement>((resolve, reject) => {
      const i = new Image()
      i.onload = () => resolve(i)
      i.onerror = reject
      i.src = prev
    })
    setBaseImage(img)
    setHistory((h) => h.slice(0, -1))
    toast.success('Undone')
  }

  const handleApplyAdjustments = async () => {
    if (!baseImage) return
    await pushHistory()

    const blob = await import('@/lib/canvasUtils').then(m =>
      m.adjustImage(baseImage, {
        brightness: adjBrightness,
        contrast: adjContrast,
        saturation: adjSaturation,
      })
    )

    const file = new File([blob], `adjusted_${Date.now()}.png`, { type: 'image/png' })
    const newAsset = await uploadAsset(projectId, file)
    const newImg = await import('@/lib/canvasUtils').then(m => m.blobToImage(blob))

    setBaseImage(newImg)
    // Reset sliders
    setAdjBrightness(1.0)
    setAdjContrast(1.0)
    setAdjSaturation(1.0)

    toast.success('Adjustments applied as new asset')
    onAssetUpdated?.(newAsset.id)
  }

  const handleClose = () => {
    setActiveJobId(null)
    onClose()
  }

  // Rectangular crop handler (full non-destructive implementation)
  const handleApplyCrop = async () => {
    if (!baseImage || !cropRect) {
      toast.error('Select a crop region first')
      return
    }

    await pushHistory()

    // Scale the UI crop rect to the actual baseImage natural size
    // The displayed image may be scaled by the browser; we use natural dimensions
    const scaleX = baseImage.naturalWidth / baseImage.width
    const scaleY = baseImage.naturalHeight / baseImage.height

    const actualRect = {
      x: Math.round(cropRect.x * scaleX),
      y: Math.round(cropRect.y * scaleY),
      width: Math.round(cropRect.width * scaleX),
      height: Math.round(cropRect.height * scaleY),
    }

    const blob = await import('@/lib/canvasUtils').then(m => m.cropImage(baseImage, actualRect))
    const file = new File([blob], `cropped_${Date.now()}.png`, { type: 'image/png' })

    const newAsset = await uploadAsset(projectId, file)
    const newImg = await import('@/lib/canvasUtils').then(m => m.blobToImage(blob))

    setBaseImage(newImg)
    setCropRect(null)
    setIsCropping(false)

    toast.success('Crop applied as new asset')
    onAssetUpdated?.(newAsset.id)
  }

  // Crop rect drawing handlers (mouse on the image area)
  const handleCropMouseDown = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!isCropping || !baseImage) return
    const rect = e.currentTarget.getBoundingClientRect()
    const x = ((e.clientX - rect.left) / rect.width) * baseImage.width
    const y = ((e.clientY - rect.top) / rect.height) * baseImage.height
    cropStartRef.current = { x, y }
    setCropRect({ x, y, width: 0, height: 0 })
  }

  const handleCropMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!isCropping || !cropStartRef.current || !baseImage) return
    const rect = e.currentTarget.getBoundingClientRect()
    const x = ((e.clientX - rect.left) / rect.width) * baseImage.width
    const y = ((e.clientY - rect.top) / rect.height) * baseImage.height

    let width = x - cropStartRef.current.x
    let height = y - cropStartRef.current.y

    // Constrain to aspect if set
    if (cropAspect) {
      const signW = width >= 0 ? 1 : -1
      const signH = height >= 0 ? 1 : -1
      const absW = Math.abs(width)
      const absH = absW / cropAspect
      width = absW * signW
      height = absH * signH
    }

    // Keep within image bounds (simple clamp)
    const startX = cropStartRef.current.x
    const startY = cropStartRef.current.y
    const finalX = Math.max(0, Math.min(baseImage.width, startX + width))
    const finalY = Math.max(0, Math.min(baseImage.height, startY + height))
    const finalW = Math.abs(finalX - startX)
    const finalH = Math.abs(finalY - startY)

    setCropRect({
      x: Math.min(startX, finalX),
      y: Math.min(startY, finalY),
      width: finalW,
      height: finalH,
    })
  }

  const handleCropMouseUp = () => {
    cropStartRef.current = null
    // Keep the rect so user can adjust or apply
  }

  // Export current mask as a Blob (binary black/white PNG)
  async function exportMaskAsBlob(): Promise<Blob | null> {
    if (!maskDataUrl) return null

    // Convert data URL to blob
    const res = await fetch(maskDataUrl)
    const blob = await res.blob()

    // For the inpaint pipeline we want a clean mask.
    // The current implementation draws white on transparent.
    // The backend pipeline expects white = area to generate.
    // This is already correct for most Diffusers inpaint pipelines.
    return blob
  }

  const handleGenerateInpaint = async () => {
    if (!assetId || !prompt.trim()) {
      toast.error('Please provide a prompt for the masked region')
      return
    }
    if (!maskDataUrl) {
      toast.error('Draw a mask on the image first')
      return
    }

    try {
      // 1. Export mask and upload as a new asset
      const maskBlob = await exportMaskAsBlob()
      if (!maskBlob) throw new Error('Could not export mask')

      const maskFile = new File([maskBlob], `mask_${Date.now()}.png`, { type: 'image/png' })
      const uploadedMask = await uploadAsset(projectId, maskFile)

      // 2. Create the image generation job (inpaint mode)
      const job = await createJob({
        job_type: 'image_generation',
        project_id: projectId,
        source_entity_type: 'keyframe',
        source_entity_id: keyframeId,
        priority: 'normal',
        params: {
          mode: 'inpaint',
          source_asset_id: assetId,
          mask_asset_id: uploadedMask.id,
          positive_prompt: prompt.trim(),
          denoise_strength: 1.0,
        },
      })

      setActiveJobId(job.id)
      toast.info('Inpaint job started — progress shown below')
    } catch (err: any) {
      console.error(err)
      toast.error(`Failed to start inpaint: ${err?.message || err}`)
    }
  }

  const handleGenerateOutpaint = async () => {
    if (!assetId || !prompt.trim()) {
      toast.error('Please provide a prompt for the outpainted region')
      return
    }

    try {
      const job = await createJob({
        job_type: 'image_generation',
        project_id: projectId,
        source_entity_type: 'keyframe',
        source_entity_id: keyframeId,
        priority: 'normal',
        params: {
          mode: 'outpaint',
          source_asset_id: assetId,
          positive_prompt: prompt.trim(),
          expand_direction: expandDirection,
          expand_amount: expandAmount,
        },
      })

      setActiveJobId(job.id)
      toast.info('Outpaint job started — progress shown below')
    } catch (err: any) {
      console.error(err)
      toast.error(`Failed to start outpaint: ${err?.message || err}`)
    }
  }

  return (
    <div className="flex flex-col h-[85vh] max-h-[820px]">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-bg-surface flex-shrink-0">
        <div>
          <div className="text-sm font-semibold text-text-primary">Canvas Editor</div>
          <div className="text-[11px] text-text-muted">Inpaint / Outpaint • Non-destructive edits</div>
        </div>
        <button onClick={handleClose} className="text-text-muted hover:text-text-primary">
          <X className="w-5 h-5" />
        </button>
      </div>

      <div className="flex flex-1 min-h-0 overflow-hidden">
        {/* Main drawing area */}
        <div className="flex-1 p-4 bg-black flex items-center justify-center overflow-auto">
          {isLoadingImage ? (
            <div className="text-text-muted">Loading image…</div>
          ) : baseImage ? (
            <div
              className="relative"
              style={{ filter: adjustmentFilter, pointerEvents: generationInProgress ? 'none' : 'auto', opacity: generationInProgress ? 0.6 : 1 }}
              onMouseDown={isCropping ? handleCropMouseDown : undefined}
              onMouseMove={isCropping ? handleCropMouseMove : undefined}
              onMouseUp={isCropping ? handleCropMouseUp : undefined}
              onMouseLeave={isCropping ? handleCropMouseUp : undefined}
            >
              <MaskCanvas
                key={maskKey}
                baseImage={baseImage}
                brushSize={brushSize}
                onMaskChange={handleMaskChange}
                className="max-h-full shadow-2xl"
              />

              {/* Live crop selection overlay (full rectangular crop UI) */}
              {isCropping && cropRect && cropRect.width > 4 && cropRect.height > 4 && (
                <div
                  className="absolute border-2 border-white shadow-[0_0_0_9999px_rgba(0,0,0,0.45)] pointer-events-none"
                  style={{
                    left: `${(cropRect.x / baseImage!.width) * 100}%`,
                    top: `${(cropRect.y / baseImage!.height) * 100}%`,
                    width: `${(cropRect.width / baseImage!.width) * 100}%`,
                    height: `${(cropRect.height / baseImage!.height) * 100}%`,
                  }}
                >
                  <div className="absolute -top-5 right-0 text-[10px] bg-black/70 text-white px-1 rounded">
                    {Math.round(cropRect.width)}×{Math.round(cropRect.height)}
                  </div>
                </div>
              )}
              {isCropping && (
                <div className="absolute top-2 left-2 text-[10px] bg-black/70 text-white px-2 py-0.5 rounded pointer-events-none">
                  Drag to select crop region {cropAspect ? `(locked ${cropAspect.toFixed(2)})` : '(free)'}
                </div>
              )}
            </div>
          ) : (
            <div className="text-text-muted">No image selected for editing</div>
          )}
        </div>

        {/* Right tools panel */}
        <div className="w-72 border-l border-border bg-bg-surface flex flex-col overflow-auto">
          <div className="p-4 space-y-6">
            {/* Brush controls */}
            <div className={generationInProgress ? 'opacity-50 pointer-events-none' : ''}>
              <div className="flex items-center justify-between mb-2">
                <div className="text-xs text-text-secondary">Brush Size</div>
                <div className="text-xs font-mono text-text-muted">{brushSize}px</div>
              </div>
              <input
                type="range"
                min={4}
                max={120}
                step={2}
                value={brushSize}
                onChange={(e) => setBrushSize(parseInt(e.target.value))}
                className="w-full accent-accent"
              />
              <div className="flex gap-2 mt-3">
                <button
                  onClick={handleClearMask}
                  className="flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 border border-border rounded-btn text-xs hover:bg-bg-subtle"
                >
                  <Trash2 className="w-3.5 h-3.5" /> Clear Mask
                </button>
                <button
                  onClick={handleInvertMask}
                  className="flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 border border-border rounded-btn text-xs hover:bg-bg-subtle"
                >
                  <RefreshCw className="w-3.5 h-3.5" /> Invert
                </button>
              </div>
            </div>

            {/* Prompt (shared) */}
            <div>
              <label className="text-xs text-text-secondary block mb-1.5">Prompt</label>
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="Describe what should appear in the edited / expanded region..."
                className="w-full h-20 bg-bg-base border border-border rounded-btn p-2 text-sm resize-y focus:outline-none focus:border-accent"
              />
              <button
                onClick={async () => {
                  if (!prompt.trim()) return
                  try {
                    await createTemplate({
                      title: prompt.slice(0, 40) || 'Canvas Prompt',
                      positive_prompt: prompt,
                      scope: 'project',
                      project_id: projectId,
                    })
                    toast.success('Prompt saved as template')
                  } catch {
                    toast.error('Failed to save template')
                  }
                }}
                disabled={!prompt.trim()}
                className="mt-1 text-[10px] px-2 py-0.5 border border-border rounded hover:bg-bg-subtle disabled:opacity-50"
              >
                Save prompt as template
              </button>
            </div>

            {/* Outpaint controls (Phase 2) */}
            <div className="pt-2 border-t border-border/60">
              <div className="text-xs text-text-secondary mb-2 font-medium">Outpaint</div>

              <div className="grid grid-cols-2 gap-2 mb-2">
                <div>
                  <label className="text-[10px] text-text-muted block mb-0.5">Direction</label>
                  <select
                    value={expandDirection}
                    onChange={(e) => setExpandDirection(e.target.value as any)}
                    className="w-full bg-bg-base border border-border rounded-btn px-2 py-1 text-sm"
                  >
                    <option value="right">Right</option>
                    <option value="left">Left</option>
                    <option value="top">Top</option>
                    <option value="bottom">Bottom</option>
                  </select>
                </div>
                <div>
                  <label className="text-[10px] text-text-muted block mb-0.5">Amount (px)</label>
                  <input
                    type="number"
                    value={expandAmount}
                    onChange={(e) => setExpandAmount(Math.max(64, parseInt(e.target.value) || 256))}
                    className="w-full bg-bg-base border border-border rounded-btn px-2 py-1 text-sm"
                    min={64}
                    step={32}
                  />
                </div>
              </div>

              <div className="text-[10px] text-text-muted">
                Expands the canvas in the chosen direction and generates new content guided by the prompt.
              </div>
            </div>

            {/* Generate actions + Progress */}
            <div className="pt-2 border-t border-border space-y-2">
              {!generationInProgress ? (
                <>
                  <button
                    onClick={handleGenerateInpaint}
                    disabled={!maskDataUrl || !prompt.trim()}
                    className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-accent text-accent-fg rounded-btn text-sm font-medium disabled:opacity-50 hover:bg-accent-hover"
                  >
                    <Wand2 className="w-4 h-4" />
                    Generate Inpaint
                  </button>

                  <button
                    onClick={handleGenerateOutpaint}
                    disabled={!prompt.trim()}
                    className="w-full flex items-center justify-center gap-2 px-4 py-2 border border-border rounded-btn text-xs hover:bg-bg-subtle disabled:opacity-50"
                  >
                    <Download className="w-3.5 h-3.5" /> Generate Outpaint
                  </button>
                </>
              ) : (
                <div className="rounded-btn border border-border bg-bg-base p-3 text-sm">
                  <div className="flex items-center gap-2 text-accent mb-2">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span className="font-medium">Generating… {generationProgress}%</span>
                  </div>

                  <div className="h-2 bg-bg-surface rounded-full overflow-hidden mb-1">
                    <div
                      className="h-2 bg-accent transition-all"
                      style={{ width: `${generationProgress}%` }}
                    />
                  </div>

                  <div className="text-[10px] text-text-muted flex justify-between">
                    <span>{generationStatus}</span>
                    {generationEta && <span>~{Math.round(generationEta)}s</span>}
                  </div>
                </div>
              )}
            </div>

            <div className="text-[10px] text-text-muted leading-snug pt-2">
              Drawing on the image creates a mask. White = area that will be regenerated.
              The result will be saved as a new asset and can be set as the keyframe’s selected image.
            </div>

            {/* Transforms & Adjustments (Phase 2/3) */}
            <div className="pt-4 border-t border-border/60 space-y-3">
              <div className="flex items-center justify-between">
                <div className="text-xs text-text-secondary font-medium">Transforms</div>
                <button
                  onClick={handleUndo}
                  disabled={history.length === 0}
                  className="text-[10px] px-2 py-0.5 border border-border rounded-btn hover:bg-bg-subtle disabled:opacity-40"
                >
                  Undo ({history.length})
                </button>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={async () => {
                    if (!baseImage) return
                    await pushHistory()
                    const blob = await import('@/lib/canvasUtils').then(m => m.flipImage(baseImage, true))
                    const file = new File([blob], `flip_h_${Date.now()}.png`, { type: 'image/png' })
                    const newAsset = await uploadAsset(projectId, file)
                    const newImg = await import('@/lib/canvasUtils').then(m => m.blobToImage(blob))
                    setBaseImage(newImg)
                    toast.success('Flipped horizontally')
                    onAssetUpdated?.(newAsset.id)
                  }}
                  className="text-xs px-3 py-1.5 border border-border rounded-btn hover:bg-bg-subtle"
                >
                  Flip H
                </button>
                <button
                  onClick={async () => {
                    if (!baseImage) return
                    await pushHistory()
                    const blob = await import('@/lib/canvasUtils').then(m => m.flipImage(baseImage, false))
                    const file = new File([blob], `flip_v_${Date.now()}.png`, { type: 'image/png' })
                    const newAsset = await uploadAsset(projectId, file)
                    const newImg = await import('@/lib/canvasUtils').then(m => m.blobToImage(blob))
                    setBaseImage(newImg)
                    toast.success('Flipped vertically')
                    onAssetUpdated?.(newAsset.id)
                  }}
                  className="text-xs px-3 py-1.5 border border-border rounded-btn hover:bg-bg-subtle"
                >
                  Flip V
                </button>
                <button
                  onClick={async () => {
                    if (!baseImage) return
                    await pushHistory()
                    const blob = await import('@/lib/canvasUtils').then(m => m.rotateImage(baseImage, 90))
                    const file = new File([blob], `rotate_${Date.now()}.png`, { type: 'image/png' })
                    const newAsset = await uploadAsset(projectId, file)
                    const newImg = await import('@/lib/canvasUtils').then(m => m.blobToImage(blob))
                    setBaseImage(newImg)
                    toast.success('Rotated 90°')
                    onAssetUpdated?.(newAsset.id)
                  }}
                  className="text-xs px-3 py-1.5 border border-border rounded-btn hover:bg-bg-subtle"
                >
                  Rotate 90°
                </button>
                <button
                  onClick={() => {
                    setIsCropping(!isCropping)
                    if (!isCropping) {
                      setCropRect(null)
                      setCropAspect(null)
                    }
                  }}
                  className={`text-xs px-3 py-1.5 border rounded-btn ${isCropping ? 'bg-accent text-accent-fg border-accent' : 'border-border hover:bg-bg-subtle'}`}
                >
                  {isCropping ? 'Exit Crop' : 'Crop'}
                </button>
              </div>

              {/* Crop aspect presets (visible when cropping) */}
              {isCropping && (
                <div className="mt-3">
                  <div className="text-xs text-text-secondary mb-1.5">Aspect Ratio</div>
                  <div className="flex flex-wrap gap-1 text-[10px]">
                    {[
                      { label: 'Free', ratio: null },
                      { label: '16:9', ratio: 16 / 9 },
                      { label: '4:3', ratio: 4 / 3 },
                      { label: '1:1', ratio: 1 },
                      { label: 'Original', ratio: baseImage ? baseImage.width / baseImage.height : null },
                    ].map(({ label, ratio }) => (
                      <button
                        key={label}
                        onClick={() => setCropAspect(ratio)}
                        className={`px-2 py-0.5 border rounded ${cropAspect === ratio ? 'bg-accent text-accent-fg border-accent' : 'border-border hover:bg-bg-subtle'}`}
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                  {cropRect && (
                    <button
                      onClick={handleApplyCrop}
                      className="mt-2 w-full text-xs py-1.5 bg-accent text-accent-fg rounded-btn hover:bg-accent-hover"
                    >
                      Apply Crop
                    </button>
                  )}
                </div>
              )}

              {/* Brightness / Contrast / Saturation with live preview */}
              <div>
                <div className="text-xs text-text-secondary mb-1.5">Adjustments (live CSS preview)</div>
                <div className="space-y-2 text-[10px]">
                  {[
                    { label: 'Brightness', value: adjBrightness, setter: setAdjBrightness, min: 0.4, max: 2.0 },
                    { label: 'Contrast', value: adjContrast, setter: setAdjContrast, min: 0.4, max: 2.0 },
                    { label: 'Saturation', value: adjSaturation, setter: setAdjSaturation, min: 0.0, max: 2.5 },
                  ].map(({ label, value, setter, min, max }) => (
                    <div key={label} className="flex items-center gap-2">
                      <span className="w-16 text-text-muted">{label}</span>
                      <input
                        type="range"
                        min={min}
                        max={max}
                        step={0.05}
                        value={value}
                        onChange={(e) => setter(parseFloat(e.target.value))}
                        className="flex-1 accent-accent"
                      />
                      <span className="w-8 text-right font-mono text-[10px] text-text-muted">{value.toFixed(2)}</span>
                    </div>
                  ))}
                </div>
                <button
                  onClick={handleApplyAdjustments}
                  disabled={adjBrightness === 1 && adjContrast === 1 && adjSaturation === 1}
                  className="mt-2 w-full text-xs py-1.5 border border-border rounded-btn hover:bg-bg-subtle disabled:opacity-50"
                >
                  Apply Adjustments (create new asset)
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom bar / Generation result */}
      <div className="flex items-center justify-between px-4 py-3 border-t border-border bg-bg-surface text-xs text-text-muted flex-shrink-0">
        {generationStatus === 'done' ? (
          <div className="flex items-center justify-between w-full text-sm">
            <span className="text-success">Generation complete! New asset created.</span>
            <button
              onClick={() => {
                setActiveJobId(null)
                onClose()
                toast.success('Check your keyframe — new variation is ready')
              }}
              className="px-4 py-1.5 bg-success text-white rounded-btn text-xs hover:bg-success/90"
            >
              Close &amp; View in Storyboard
            </button>
          </div>
        ) : generationStatus === 'failed' ? (
          <div className="flex items-center justify-between w-full">
            <span className="text-error flex items-center gap-1"><AlertCircle className="w-3 h-3" /> Generation failed. Check Jobs panel for details and suggested fixes.</span>
            <button onClick={handleClose} className="px-3 py-1 border border-border rounded-btn text-xs">
              Close
            </button>
          </div>
        ) : (
          <>
            <div>Draw mask for Inpaint • Use Outpaint controls • Apply transforms with history</div>
            <button onClick={handleClose} className="hover:text-text-primary">
              Cancel
            </button>
          </>
        )}
      </div>
    </div>
  )
}
