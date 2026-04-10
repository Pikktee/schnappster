"use client"

import { useMemo } from "react"
import { Check, X } from "lucide-react"
import { cn } from "@/lib/utils"
import {
  checkPassword,
  getPasswordStrength,
  type PasswordStrength,
} from "@/lib/password-validation"

const STRENGTH_CONFIG: Record<
  Exclude<PasswordStrength, "none">,
  { label: string; color: string; barColor: string; segments: number }
> = {
  weak: {
    label: "Schwach",
    color: "text-red-600 dark:text-red-400",
    barColor: "bg-red-500",
    segments: 1,
  },
  medium: {
    label: "Mittel",
    color: "text-amber-600 dark:text-amber-400",
    barColor: "bg-amber-500",
    segments: 2,
  },
  strong: {
    label: "Stark",
    color: "text-green-600 dark:text-green-400",
    barColor: "bg-green-500",
    segments: 3,
  },
}

const CRITERIA = [
  { key: "minLength" as const, label: "Mindestens 8 Zeichen" },
  { key: "hasUppercase" as const, label: "Grossbuchstabe (A-Z)" },
  { key: "hasLowercase" as const, label: "Kleinbuchstabe (a-z)" },
  { key: "hasSpecialChar" as const, label: "Sonderzeichen (!@#$...)" },
]

export function PasswordStrengthIndicator({ password }: { password: string }) {
  const strength = useMemo(() => getPasswordStrength(password), [password])
  const checks = useMemo(() => checkPassword(password), [password])

  if (strength === "none") return null

  const config = STRENGTH_CONFIG[strength]

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <div className="flex flex-1 gap-1">
          {[1, 2, 3].map((segment) => (
            <div
              key={segment}
              className={cn(
                "h-1.5 flex-1 rounded-full transition-colors duration-300",
                segment <= config.segments ? config.barColor : "bg-muted",
              )}
            />
          ))}
        </div>
        <span className={cn("text-xs font-medium", config.color)}>{config.label}</span>
      </div>
      <ul className="space-y-0.5">
        {CRITERIA.map(({ key, label }) => (
          <li key={key} className="flex items-center gap-1.5 text-xs">
            {checks[key] ? (
              <Check className="size-3 text-green-600 dark:text-green-400" />
            ) : (
              <X className="size-3 text-muted-foreground/60" />
            )}
            <span
              className={cn(
                checks[key]
                  ? "text-green-700 dark:text-green-400"
                  : "text-muted-foreground",
              )}
            >
              {label}
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}
