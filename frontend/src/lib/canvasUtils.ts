/**
 * Canvas-based image transform utilities for the Canvas Editor.
 * All functions return a Blob (PNG) ready for upload as a new Asset.
 */

export async function flipImage(
  source: HTMLImageElement | HTMLCanvasElement,
  horizontal: boolean
): Promise<Blob> {
  const canvas = document.createElement('canvas')
  const ctx = canvas.getContext('2d', { willReadFrequently: true })!

  canvas.width = source.width
  canvas.height = source.height

  ctx.save()
  if (horizontal) {
    ctx.translate(canvas.width, 0)
    ctx.scale(-1, 1)
  } else {
    ctx.translate(0, canvas.height)
    ctx.scale(1, -1)
  }
  ctx.drawImage(source as any, 0, 0)
  ctx.restore()

  return new Promise((resolve) => canvas.toBlob((b) => resolve(b!), 'image/png'))
}

export async function rotateImage(
  source: HTMLImageElement | HTMLCanvasElement,
  degrees: 90 | 180 | 270
): Promise<Blob> {
  const canvas = document.createElement('canvas')
  const ctx = canvas.getContext('2d', { willReadFrequently: true })!

  const rad = (degrees * Math.PI) / 180

  if (degrees === 90 || degrees === 270) {
    canvas.width = source.height
    canvas.height = source.width
  } else {
    canvas.width = source.width
    canvas.height = source.height
  }

  ctx.translate(canvas.width / 2, canvas.height / 2)
  ctx.rotate(rad)
  ctx.drawImage(source as any, -source.width / 2, -source.height / 2)

  return new Promise((resolve) => canvas.toBlob((b) => resolve(b!), 'image/png'))
}

export async function adjustImage(
  source: HTMLImageElement | HTMLCanvasElement,
  adjustments: { brightness?: number; contrast?: number; saturation?: number }
): Promise<Blob> {
  const canvas = document.createElement('canvas')
  const ctx = canvas.getContext('2d', { willReadFrequently: true })!

  canvas.width = source.width
  canvas.height = source.height

  const { brightness = 1, contrast = 1, saturation = 1 } = adjustments

  // Use ctx.filter for fast, good quality adjustment (supported in modern browsers)
  ctx.filter = `
    brightness(${brightness})
    contrast(${contrast})
    saturate(${saturation})
  `.trim()

  ctx.drawImage(source as any, 0, 0)

  // Reset filter
  ctx.filter = 'none'

  return new Promise((resolve) => canvas.toBlob((b) => resolve(b!), 'image/png'))
}

export async function cropImage(
  source: HTMLImageElement | HTMLCanvasElement,
  rect: { x: number; y: number; width: number; height: number }
): Promise<Blob> {
  const canvas = document.createElement('canvas')
  const ctx = canvas.getContext('2d', { willReadFrequently: true })!

  canvas.width = rect.width
  canvas.height = rect.height

  ctx.drawImage(
    source as any,
    rect.x, rect.y, rect.width, rect.height,
    0, 0, rect.width, rect.height
  )

  return new Promise((resolve) => canvas.toBlob((b) => resolve(b!), 'image/png'))
}

/**
 * Helper to load a Blob into an Image for further use in the editor.
 */
export function blobToImage(blob: Blob): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(blob)
    const img = new Image()
    img.onload = () => {
      URL.revokeObjectURL(url)
      resolve(img)
    }
    img.onerror = reject
    img.src = url
  })
}
