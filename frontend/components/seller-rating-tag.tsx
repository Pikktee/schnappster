import { cn } from "@/lib/utils"
import { getSellerRatingLabel } from "@/lib/format"

interface SellerRatingTagProps {
  rating: number | null
}

export function SellerRatingTag({ rating }: SellerRatingTagProps) {
  const { label, color } = getSellerRatingLabel(rating)
  return (
    <span className={cn("inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium", color)}>
      {label}
    </span>
  )
}
