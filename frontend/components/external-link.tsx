import { ExternalLink as ExternalLinkIcon } from "lucide-react"

interface ExternalLinkProps {
  href: string
  children: React.ReactNode
  className?: string
}

export function ExternalLink({ href, children, className }: ExternalLinkProps) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className={`inline-flex items-center gap-1 text-primary hover:underline cursor-pointer ${className || ""}`}
    >
      {children}
      <ExternalLinkIcon className="size-3 shrink-0" />
    </a>
  )
}
