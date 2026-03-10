import { ExternalLink as ExternalLinkIcon } from "lucide-react"
import { cn } from "@/lib/utils"

interface ExternalLinkProps {
  href: string
  children: React.ReactNode
  className?: string
  title?: string
}

export function ExternalLink({ href, children, className, title }: ExternalLinkProps) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className={cn("inline-flex items-center gap-1 text-link hover:underline cursor-pointer", className)}
      aria-label={`${typeof children === "string" ? children : ""} (öffnet neues Fenster)`}
      title={title}
    >
      {children}
      <ExternalLinkIcon className="size-3 shrink-0" aria-hidden="true" />
    </a>
  )
}
