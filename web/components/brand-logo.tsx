import type { CSSProperties } from "react"
import { cn } from "@/lib/utils"

type OwlMarkProps = { size?: number; className?: string }

/** Static Schnappster owl mark (no animation) for logos and favicons. */
export function OwlMark({ size = 40, className }: OwlMarkProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 200 200"
      className={className}
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden
    >
      <ellipse cx="100" cy="120" rx="60" ry="65" fill="#F59E0B" />
      <ellipse cx="100" cy="130" rx="40" ry="45" fill="#FEF3C7" />
      <path d="M50 110 Q35 140 55 165 Q70 150 65 115 Z" fill="#D97706" />
      <path d="M150 110 Q165 140 145 165 Q130 150 135 115 Z" fill="#D97706" />
      <path d="M65 65 L55 40 L75 60 Z" fill="#D97706" />
      <path d="M135 65 L145 40 L125 60 Z" fill="#D97706" />
      <circle cx="80" cy="85" r="20" fill="#fff" />
      <circle cx="82" cy="87" r="9" fill="#1C1917" />
      <circle cx="85" cy="84" r="3" fill="#fff" />
      <circle cx="120" cy="85" r="20" fill="#fff" />
      <circle cx="118" cy="87" r="9" fill="#1C1917" />
      <circle cx="121" cy="84" r="3" fill="#fff" />
      <path d="M100 100 L93 112 L107 112 Z" fill="#D97706" />
      <path
        d="M85 180 L82 192 M90 180 L92 192 M95 180 L102 192"
        stroke="#D97706"
        strokeWidth="3"
        strokeLinecap="round"
      />
      <path
        d="M115 180 L118 192 M110 180 L108 192 M105 180 L98 192"
        stroke="#D97706"
        strokeWidth="3"
        strokeLinecap="round"
      />
      <path d="M130 125 L170 125 L180 140 L170 155 L130 155 Z" fill="#10B981" />
      <circle cx="172" cy="140" r="3" fill="#FAFAF9" />
      <text x="138" y="146" fill="#fff" fontSize="14" fontWeight="700" fontFamily="Lexend">
        €
      </text>
      <path
        d="M152 138 L152 148 M148 144 L152 148 L156 144"
        stroke="#fff"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
    </svg>
  )
}

const wordmarkStyle: CSSProperties = {
  fontFamily: "'Fredoka', 'Baloo 2', 'Poppins', system-ui, sans-serif",
  fontWeight: 400,
  lineHeight: 1,
  letterSpacing: "-0.015em",
  color: "#1C1917",
}

type BrandLogoProps = { owlSize?: number; className?: string; textClassName?: string }

/** Owl mark + two-tone "Schnappster" wordmark, matching the marketing landing. */
export function BrandLogo({ owlSize = 36, className, textClassName = "text-xl" }: BrandLogoProps) {
  return (
    <span className={cn("flex items-center gap-2 leading-none", className)}>
      <OwlMark size={owlSize} />
      <span className={textClassName} style={wordmarkStyle}>
        Schnapp<span style={{ color: "#D97706" }}>ster</span>
      </span>
    </span>
  )
}
