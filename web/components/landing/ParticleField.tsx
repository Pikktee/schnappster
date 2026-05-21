"use client"

import { useEffect, useRef } from "react"

type Particle = {
  x: number
  y: number
  vx: number
  vy: number
  r: number
  color: string
}

const AMBER = "#F59E0B"
const GREEN = "#10B981"

export function ParticleField() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const wrapRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    const wrap = wrapRef.current
    if (!canvas || !wrap) return
    const ctx = canvas.getContext("2d")
    if (!ctx) return

    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches

    let width = 0
    let height = 0
    let dpr = Math.min(window.devicePixelRatio || 1, 2)
    let particles: Particle[] = []
    const mouse = { x: -9999, y: -9999, active: false }
    let visible = true
    let rafId = 0

    const targetCount = () => {
      const area = width * height
      // density tuned so ~80 on a ~1280x720 hero
      const base = Math.round(area / 22000)
      return Math.max(20, Math.min(85, base))
    }

    const spawn = (count: number) => {
      particles = []
      for (let i = 0; i < count; i++) {
        // Higher density on the right: biased x-position with sqrt distribution
        const bias = Math.pow(Math.random(), 0.55) // skews toward 1
        const x = bias * width
        const y = Math.random() * height
        const speed = 0.04 + Math.random() * 0.07
        const angle = Math.random() * Math.PI * 2
        const isGreen = Math.random() < 0.15
        particles.push({
          x,
          y,
          vx: Math.cos(angle) * speed,
          vy: Math.sin(angle) * speed,
          r: 1 + Math.random() * 2,
          color: isGreen ? GREEN : AMBER,
        })
      }
    }

    const resize = () => {
      const rect = wrap.getBoundingClientRect()
      width = rect.width
      height = rect.height
      dpr = Math.min(window.devicePixelRatio || 1, 2)
      canvas.width = Math.floor(width * dpr)
      canvas.height = Math.floor(height * dpr)
      canvas.style.width = `${width}px`
      canvas.style.height = `${height}px`
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      spawn(targetCount())
    }

    const onMouseMove = (e: MouseEvent) => {
      const rect = wrap.getBoundingClientRect()
      const x = e.clientX - rect.left
      const y = e.clientY - rect.top
      // Only treat as active if cursor is within the hero bounds
      if (x >= 0 && x <= rect.width && y >= 0 && y <= rect.height) {
        mouse.x = x
        mouse.y = y
        mouse.active = true
      } else {
        mouse.active = false
        mouse.x = -9999
        mouse.y = -9999
      }
    }
    const onMouseLeaveWindow = () => {
      mouse.active = false
      mouse.x = -9999
      mouse.y = -9999
    }

    const step = () => {
      ctx.clearRect(0, 0, width, height)

      const repelRadius = 120
      const repelRadiusSq = repelRadius * repelRadius
      const linkDist = 120
      const linkDistSq = linkDist * linkDist

      // Update
      for (let i = 0; i < particles.length; i++) {
        const p = particles[i]
        if (!reduce) {
          p.x += p.vx
          p.y += p.vy
        }

        // Mouse repel
        if (mouse.active) {
          const dx = p.x - mouse.x
          const dy = p.y - mouse.y
          const d2 = dx * dx + dy * dy
          if (d2 < repelRadiusSq && d2 > 0.01) {
            const d = Math.sqrt(d2)
            const force = (1 - d / repelRadius) * 1.2
            p.x += (dx / d) * force
            p.y += (dy / d) * force
          }
        }

        // Wrap
        if (p.x < -10) p.x = width + 10
        if (p.x > width + 10) p.x = -10
        if (p.y < -10) p.y = height + 10
        if (p.y > height + 10) p.y = -10
      }

      // Draw links
      ctx.lineWidth = 1
      for (let i = 0; i < particles.length; i++) {
        const a = particles[i]
        for (let j = i + 1; j < particles.length; j++) {
          const b = particles[j]
          const dx = a.x - b.x
          const dy = a.y - b.y
          const d2 = dx * dx + dy * dy
          if (d2 < linkDistSq) {
            const alpha = (1 - d2 / linkDistSq) * 0.22
            // Fade further on the left to keep headline readable
            const midX = (a.x + b.x) * 0.5
            const leftFade = Math.min(1, Math.max(0.15, midX / (width * 0.55)))
            ctx.strokeStyle = `rgba(245, 158, 11, ${alpha * leftFade})`
            ctx.beginPath()
            ctx.moveTo(a.x, a.y)
            ctx.lineTo(b.x, b.y)
            ctx.stroke()
          }
        }
      }

      // Draw particles
      for (const p of particles) {
        const leftFade = Math.min(1, Math.max(0.25, p.x / (width * 0.55)))
        ctx.fillStyle =
          p.color === GREEN
            ? `rgba(16, 185, 129, ${0.85 * leftFade})`
            : `rgba(245, 158, 11, ${0.85 * leftFade})`
        ctx.beginPath()
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2)
        ctx.fill()
      }

      rafId = requestAnimationFrame(step)
    }

    const start = () => {
      if (rafId) return
      rafId = requestAnimationFrame(step)
    }
    const stop = () => {
      if (rafId) cancelAnimationFrame(rafId)
      rafId = 0
    }

    resize()
    start()

    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          visible = e.isIntersecting
          if (visible) start()
          else stop()
        }
      },
      { threshold: 0 },
    )
    io.observe(wrap)

    const ro = new ResizeObserver(() => resize())
    ro.observe(wrap)

    window.addEventListener("mousemove", onMouseMove, { passive: true })
    const onWindowMouseOut = (e: MouseEvent) => {
      if (!e.relatedTarget) onMouseLeaveWindow()
    }
    window.addEventListener("mouseout", onWindowMouseOut)
    window.addEventListener("blur", onMouseLeaveWindow)
    const onVisibility = () => {
      if (document.hidden) stop()
      else if (visible) start()
    }
    document.addEventListener("visibilitychange", onVisibility)

    return () => {
      stop()
      io.disconnect()
      ro.disconnect()
      window.removeEventListener("mousemove", onMouseMove)
      window.removeEventListener("mouseout", onWindowMouseOut)
      window.removeEventListener("blur", onMouseLeaveWindow)
      document.removeEventListener("visibilitychange", onVisibility)
    }
  }, [])

  return (
    <div ref={wrapRef} className="absolute inset-0 pointer-events-none">
      <canvas ref={canvasRef} className="block w-full h-full pointer-events-none" />
    </div>
  )
}
