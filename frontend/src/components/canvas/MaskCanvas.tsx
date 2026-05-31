import React, { useRef, useEffect, useState, useCallback } from 'react'

interface MaskCanvasProps {
  /** The base image to display under the mask overlay */
  baseImage: HTMLImageElement | null
  /** Current brush size in pixels */
  brushSize?: number
  /** Called whenever the mask changes (with a data URL of the mask) */
  onMaskChange?: (maskDataUrl: string | null) => void
  /** Optional className for the container */
  className?: string
}

export default function MaskCanvas({
  baseImage,
  brushSize = 24,
  onMaskChange,
  className = '',
}: MaskCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const baseCanvasRef = useRef<HTMLCanvasElement>(null)
  const maskCanvasRef = useRef<HTMLCanvasElement>(null)

  const [isDrawing, setIsDrawing] = useState(false)
  const [lastPos, setLastPos] = useState<{ x: number; y: number } | null>(null)

  // Draw the base image onto the base canvas
  const drawBaseImage = useCallback(() => {
    const baseCanvas = baseCanvasRef.current
    if (!baseCanvas || !baseImage) return

    const ctx = baseCanvas.getContext('2d', { willReadFrequently: true })
    if (!ctx) return

    baseCanvas.width = baseImage.width
    baseCanvas.height = baseImage.height

    ctx.clearRect(0, 0, baseCanvas.width, baseCanvas.height)
    ctx.drawImage(baseImage, 0, 0)
  }, [baseImage])

  // Resize canvases to match the base image (or container)
  const resizeCanvases = useCallback(() => {
    if (!baseImage) return

    const baseCanvas = baseCanvasRef.current
    const maskCanvas = maskCanvasRef.current
    if (!baseCanvas || !maskCanvas) return

    const container = containerRef.current
    const maxW = container?.clientWidth || 800
    const maxH = container?.clientHeight || 600

    // Maintain aspect ratio
    const scale = Math.min(maxW / baseImage.width, maxH / baseImage.height, 1)
    const displayW = Math.floor(baseImage.width * scale)
    const displayH = Math.floor(baseImage.height * scale)

    // Set display size via CSS
    baseCanvas.style.width = `${displayW}px`
    baseCanvas.style.height = `${displayH}px`
    maskCanvas.style.width = `${displayW}px`
    maskCanvas.style.height = `${displayH}px`

    // Set internal resolution to full image resolution for crisp masks
    baseCanvas.width = baseImage.width
    baseCanvas.height = baseImage.height
    maskCanvas.width = baseImage.width
    maskCanvas.height = baseImage.height

    drawBaseImage()

    // Clear mask
    const maskCtx = maskCanvas.getContext('2d', { willReadFrequently: true })
    if (maskCtx) {
      maskCtx.clearRect(0, 0, maskCanvas.width, maskCanvas.height)
    }
  }, [baseImage, drawBaseImage])

  // Initialize / re-draw when baseImage changes
  useEffect(() => {
    if (baseImage) {
      resizeCanvases()
    }
  }, [baseImage, resizeCanvases])

  // Get pointer position relative to the canvas (in canvas coordinate space)
  const getCanvasPos = (e: React.MouseEvent | React.TouchEvent): { x: number; y: number } | null => {
    const canvas = maskCanvasRef.current
    if (!canvas) return null

    const rect = canvas.getBoundingClientRect()
    const clientX = 'touches' in e ? e.touches[0].clientX : (e as React.MouseEvent).clientX
    const clientY = 'touches' in e ? e.touches[0].clientY : (e as React.MouseEvent).clientY

    // Scale from display size back to internal resolution
    const scaleX = canvas.width / rect.width
    const scaleY = canvas.height / rect.height

    return {
      x: (clientX - rect.left) * scaleX,
      y: (clientY - rect.top) * scaleY,
    }
  }

  const drawMaskStroke = (ctx: CanvasRenderingContext2D, from: { x: number; y: number }, to: { x: number; y: number }, size: number) => {
    ctx.strokeStyle = 'white'
    ctx.lineWidth = size
    ctx.lineCap = 'round'
    ctx.lineJoin = 'round'
    ctx.globalCompositeOperation = 'source-over'

    ctx.beginPath()
    ctx.moveTo(from.x, from.y)
    ctx.lineTo(to.x, to.y)
    ctx.stroke()
  }

  const startDrawing = (e: React.MouseEvent | React.TouchEvent) => {
    const pos = getCanvasPos(e)
    if (!pos) return

    const maskCanvas = maskCanvasRef.current
    const ctx = maskCanvas?.getContext('2d', { willReadFrequently: true })
    if (!ctx) return

    setIsDrawing(true)
    setLastPos(pos)

    // Draw a dot at start position
    ctx.fillStyle = 'white'
    ctx.beginPath()
    ctx.arc(pos.x, pos.y, brushSize / 2, 0, Math.PI * 2)
    ctx.fill()

    notifyMaskChange()
  }

  const draw = (e: React.MouseEvent | React.TouchEvent) => {
    if (!isDrawing) return
    const pos = getCanvasPos(e)
    if (!pos || !lastPos) return

    const maskCanvas = maskCanvasRef.current
    const ctx = maskCanvas?.getContext('2d', { willReadFrequently: true })
    if (!ctx) return

    drawMaskStroke(ctx, lastPos, pos, brushSize)
    setLastPos(pos)

    notifyMaskChange()
  }

  const endDrawing = () => {
    setIsDrawing(false)
    setLastPos(null)
  }

  const notifyMaskChange = () => {
    if (!onMaskChange) return
    const maskCanvas = maskCanvasRef.current
    if (!maskCanvas) {
      onMaskChange(null)
      return
    }
    // Export the mask as data URL (white strokes on transparent)
    const dataUrl = maskCanvas.toDataURL('image/png')
    onMaskChange(dataUrl)
  }

  // Public methods exposed via ref (for parent to call Clear / Invert)
  const clearMask = () => {
    const maskCanvas = maskCanvasRef.current
    const ctx = maskCanvas?.getContext('2d')
    if (ctx && maskCanvas) {
      ctx.clearRect(0, 0, maskCanvas.width, maskCanvas.height)
      notifyMaskChange()
    }
  }

  const invertMask = () => {
    const maskCanvas = maskCanvasRef.current
    const ctx = maskCanvas?.getContext('2d', { willReadFrequently: true })
    if (!ctx || !maskCanvas) return

    const imageData = ctx.getImageData(0, 0, maskCanvas.width, maskCanvas.height)
    const data = imageData.data

    for (let i = 0; i < data.length; i += 4) {
      // Invert the alpha channel (white <-> transparent in our drawing model)
      const alpha = data[i + 3]
      data[i] = 255
      data[i + 1] = 255
      data[i + 2] = 255
      data[i + 3] = 255 - alpha
    }

    ctx.putImageData(imageData, 0, 0)
    notifyMaskChange()
  }

  // No imperative handle exposed for now (clear/invert handled via parent state + key remount)

  return (
    <div
      ref={containerRef}
      className={`relative overflow-hidden rounded-lg border border-border bg-black ${className}`}
      style={{ touchAction: 'none' }}
    >
      <canvas
        ref={baseCanvasRef}
        className="absolute left-0 top-0"
        style={{ imageRendering: 'pixelated' }}
      />
      <canvas
        ref={maskCanvasRef}
        className="absolute left-0 top-0 cursor-crosshair"
        style={{ mixBlendMode: 'screen' }} // nice red-ish overlay feel when we draw white
        onMouseDown={startDrawing}
        onMouseMove={draw}
        onMouseUp={endDrawing}
        onMouseLeave={endDrawing}
        onTouchStart={startDrawing}
        onTouchMove={draw}
        onTouchEnd={endDrawing}
      />
      {!baseImage && (
        <div className="absolute inset-0 flex items-center justify-center text-text-muted text-sm">
          No image loaded
        </div>
      )}
    </div>
  )
}
