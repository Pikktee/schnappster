"use client"

import { cn } from "@/lib/utils"

export function ContentReveal({
  className,
  children,
  ...props
}: React.ComponentProps<"div">) {
  return (
    <div className={cn("content-reveal", className)} {...props}>
      {children}
    </div>
  )
}
