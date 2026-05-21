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
    const onMove = (e: MouseEvent) => {
      const svg = svgRef.current
      if (!svg) return
      const r = svg.getBoundingClientRect()
      const cx = r.left + r.width / 2
      const cy = r.top + r.height * (85 / 200)
      const dx = e.clientX - cx
      const dy = e.clientY - cy
      const dist = Math.hypot(dx, dy) || 1
      // Eye white r = 20, pupil r = 9, highlight reaches ~3px further → safe max ≈ 6.5
      const maxOffset = 6.5
      const mag = Math.min(maxOffset, dist / 28)
      const nx = (dx / dist) * mag
      const ny = (dy / dist) * mag
      if (leftPupil.current)
        leftPupil.current.style.transform = `translate(${nx}px, ${ny}px)`
      if (rightPupil.current)
        rightPupil.current.style.transform = `translate(${nx}px, ${ny}px)`
    }
    window.addEventListener("mousemove", onMove, { passive: true })
    return () => window.removeEventListener("mousemove", onMove)
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
        @keyframes owl-tag-swing {
          0%   { transform: rotate(-15deg); }
          30%  { transform: rotate(-26deg); }
          65%  { transform: rotate(-8deg); }
          100% { transform: rotate(-15deg); }
        }

        .owl-root      { cursor: pointer; }
        .owl-float     { animation: owl-float 3s ease-in-out infinite;
                          transform-box: fill-box; transform-origin: center; }
        .owl-tilt      { transition: transform 500ms cubic-bezier(0.22, 1, 0.36, 1);
                          transform-box: fill-box; transform-origin: 100px 130px; }
        .owl-root:hover .owl-tilt { transform: rotate(-4deg); }

        .owl-tag       { animation: owl-tag-idle 4.5s ease-in-out infinite;
                          transform-box: fill-box; transform-origin: top left; }
        .owl-root:hover .owl-tag {
          animation: owl-tag-swing 900ms cubic-bezier(0.22, 1, 0.36, 1);
          animation-fill-mode: both;
        }

        .owl-pupil     { transition: transform 320ms cubic-bezier(0.22, 1, 0.36, 1); }

        @media (prefers-reduced-motion: reduce) {
          .owl-float, .owl-tag, .owl-tilt { animation: none !important; transition: none !important; }
          .owl-root:hover .owl-tilt { transform: none !important; }
          .owl-root:hover .owl-tag  { animation: none !important; }
          .owl-pupil { transition: none !important; transform: none !important; }
        }
      `}</style>

      <g className="owl-root">
        <g className="owl-float">
          <g className="owl-tilt">
            {/* Body */}
            <ellipse cx="100" cy="120" rx="60" ry="65" fill="#F59E0B" />
            <ellipse cx="100" cy="130" rx="40" ry="45" fill="#FEF3C7" />

            {/* Wings */}
            <path d="M50 110 Q35 140 55 165 Q70 150 65 115 Z" fill="#D97706" />
            <path d="M150 110 Q165 140 145 165 Q130 150 135 115 Z" fill="#D97706" />

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

            {/* Price tag */}
            <g className="owl-tag">
              <path d="M130 125 L170 125 L180 140 L170 155 L130 155 Z" fill="#10B981" />
              <circle cx="172" cy="140" r="3" fill="#FAFAF9" />
              <text x="138" y="146" fill="#fff" fontSize="14" fontWeight="700" fontFamily="Lexend">€</text>
              <path d="M152 138 L152 148 M148 144 L152 148 L156 144" stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="none" />
            </g>
          </g>
        </g>
      </g>
    </svg>
  )
}
