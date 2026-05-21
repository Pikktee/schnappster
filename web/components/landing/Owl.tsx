"use client"

import { useEffect, useRef, useState } from "react"

type Props = { size?: number; className?: string }

export function Owl({ size = 120, className }: Props) {
  const svgRef = useRef<SVGSVGElement>(null)
  const leftPupil = useRef<SVGGElement>(null)
  const rightPupil = useRef<SVGGElement>(null)
  const [reduce, setReduce] = useState(false)

  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)")
    const apply = () => setReduce(mq.matches)
    apply()
    mq.addEventListener("change", apply)
    return () => mq.removeEventListener("change", apply)
  }, [])

  useEffect(() => {
    if (reduce) return

    // Eyes react with a short latency, like a real reaction time: the pupils
    // target where the cursor was REACTION_MS ago. When the cursor jumps, they
    // hold their position briefly, then move to follow.
    const REACTION_MS = 250
    type Sample = { t: number; x: number; y: number }
    const samples: Sample[] = [{ t: performance.now(), x: 0, y: 0 }]
    const current = { x: 0, y: 0 }
    let rafId = 0

    const onMove = (e: MouseEvent) => {
      const svg = svgRef.current
      if (!svg) return
      const r = svg.getBoundingClientRect()
      const cx = r.left + r.width / 2
      const cy = r.top + r.height * (85 / 200)
      const dx = e.clientX - cx
      const dy = e.clientY - cy
      const dist = Math.hypot(dx, dy) || 1
      // Pupil base offset ≈2.8px + radius 9 must stay within eye-white radius 20 → safe max ≈ 8
      const maxOffset = 8
      const mag = Math.min(maxOffset, dist / 28)
      samples.push({ t: performance.now(), x: (dx / dist) * mag, y: (dy / dist) * mag })
    }

    const tick = () => {
      const cutoff = performance.now() - REACTION_MS
      // Advance to the most recent sample already older than the reaction delay.
      while (samples.length > 1 && samples[1].t <= cutoff) samples.shift()
      const delayed = samples[0]
      // Quick, smooth catch-up once the reaction delay has elapsed.
      const ease = 0.35
      current.x += (delayed.x - current.x) * ease
      current.y += (delayed.y - current.y) * ease
      const transform = `translate(${current.x.toFixed(2)}px, ${current.y.toFixed(2)}px)`
      if (leftPupil.current) leftPupil.current.style.transform = transform
      if (rightPupil.current) rightPupil.current.style.transform = transform
      rafId = requestAnimationFrame(tick)
    }

    window.addEventListener("mousemove", onMove, { passive: true })
    rafId = requestAnimationFrame(tick)
    return () => {
      window.removeEventListener("mousemove", onMove)
      cancelAnimationFrame(rafId)
    }
  }, [reduce])

  return (
    <svg
      ref={svgRef}
      width={size}
      height={size}
      viewBox="0 0 200 200"
      className={className}
      xmlns="http://www.w3.org/2000/svg"
      style={{ overflow: "visible" }}
    >
      <style>{`
        @keyframes owl-float { 0%,100% { transform: translateY(0); } 50% { transform: translateY(-6px); } }
        @keyframes owl-tag-idle {
          0%,100% { transform: rotate(-15deg); }
          50%     { transform: rotate(-12deg); }
        }
        @keyframes owl-arm-swing {
          0%   { transform: rotate(0deg); }
          30%  { transform: rotate(-11deg); }
          65%  { transform: rotate(4deg); }
          100% { transform: rotate(0deg); }
        }

        .owl-root      { cursor: pointer; }
        .owl-float     { animation: owl-float 3s ease-in-out infinite;
                          transform-box: fill-box; transform-origin: center; }
        .owl-tilt      { transition: transform 500ms cubic-bezier(0.22, 1, 0.36, 1);
                          transform-box: fill-box; transform-origin: 100px 130px; }
        .owl-root:hover .owl-tilt { transform: rotate(-4deg); }

        .owl-tag       { animation: owl-tag-idle 4.5s ease-in-out infinite;
                          transform-box: fill-box; transform-origin: top left; }

        /* Hand + tag swing together as one arm on hover */
        .owl-arm       { transform-box: fill-box; transform-origin: 31% 7%; }
        .owl-root:hover .owl-arm {
          animation: owl-arm-swing 900ms cubic-bezier(0.22, 1, 0.36, 1);
          animation-fill-mode: both;
        }

        .owl-pupil     { will-change: transform; }

        @media (prefers-reduced-motion: reduce) {
          .owl-float, .owl-tag, .owl-tilt, .owl-arm { animation: none !important; transition: none !important; }
          .owl-root:hover .owl-tilt { transform: none !important; }
          .owl-root:hover .owl-arm  { animation: none !important; transform: none !important; }
          .owl-pupil { transition: none !important; transform: none !important; }
        }
      `}</style>

      <g className="owl-root">
        <g className="owl-float">
          <g className="owl-tilt">
            {/* Body */}
            <ellipse cx="100" cy="120" rx="60" ry="65" fill="#F59E0B" />
            <ellipse cx="100" cy="130" rx="40" ry="45" fill="#FEF3C7" />

            {/* Wings (left only; right wing lives in the arm group with the tag) */}
            <path d="M50 110 Q35 140 55 165 Q70 150 65 115 Z" fill="#D97706" />

            {/* Head tufts */}
            <path d="M65 65 L55 40 L75 60 Z" fill="#D97706" />
            <path d="M135 65 L145 40 L125 60 Z" fill="#D97706" />

            {/* Left eye */}
            <circle cx="80" cy="85" r="20" fill="#fff" />
            <g ref={leftPupil} className="owl-pupil">
              <circle cx="82" cy="87" r="9" fill="#1C1917" />
              <circle cx="85" cy="84" r="3" fill="#fff" />
            </g>

            {/* Right eye */}
            <circle cx="120" cy="85" r="20" fill="#fff" />
            <g ref={rightPupil} className="owl-pupil">
              <circle cx="118" cy="87" r="9" fill="#1C1917" />
              <circle cx="121" cy="84" r="3" fill="#fff" />
            </g>

            {/* Beak */}
            <path d="M100 100 L93 112 L107 112 Z" fill="#D97706" />

            {/* Feet */}
            <path d="M85 180 L82 192 M90 180 L92 192 M95 180 L102 192" stroke="#D97706" strokeWidth="3" strokeLinecap="round" />
            <path d="M115 180 L118 192 M110 180 L108 192 M105 180 L98 192" stroke="#D97706" strokeWidth="3" strokeLinecap="round" />

            {/* Right wing (hand) + price tag — swing together on hover */}
            <g className="owl-arm">
              <path d="M150 110 Q165 140 145 165 Q130 150 135 115 Z" fill="#D97706" />
              <g className="owl-tag">
                <path d="M138 120 L178 120 L188 135 L178 150 L138 150 Z" fill="#10B981" />
                <circle cx="180" cy="135" r="3" fill="#FAFAF9" />
                <text x="146" y="141" fill="#fff" fontSize="14" fontWeight="700" fontFamily="Lexend">€</text>
                <path d="M160 133 L160 143 M156 139 L160 143 L164 139" stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="none" />
              </g>
            </g>
          </g>
        </g>
      </g>
    </svg>
  )
}
