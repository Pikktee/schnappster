"use client"

import { useEffect, useMemo, useState, useCallback, useRef } from "react"
import { usePathname, useRouter } from "next/navigation"
import Image from "next/image"
import {
  ArrowLeft,
  ExternalLink as ExternalLinkIcon,
  Package,
  ChevronDown,
  ChevronUp,
  ChevronLeft,
  ChevronRight,
  ThumbsUp,
  ShieldCheck,
  User,
  Sparkles,
} from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"
import { ScoreBadge } from "@/components/score-badge"
import { SellerRatingTag } from "@/components/seller-rating-tag"
import { ExternalLink } from "@/components/external-link"
import { fetchAd, fetchSearch } from "@/lib/api"
import type { Ad, AdSearch } from "@/lib/types"
import {
  formatPrice,
  timeAgo,
  getAdImageUrls,
} from "@/lib/format"
import { toast } from "sonner"
import { Skeleton } from "@/components/ui/skeleton"

export function AdDetailPage() {
  const router = useRouter()
  const pathname = usePathname()
  const [id, setId] = useState<number>(NaN)

  useEffect(() => {
    const match = window.location.pathname.match(/\/(\d+)\/?$/)
    if (match) setId(Number(match[1]))
  }, [pathname])

  const [ad, setAd] = useState<Ad | null>(null)
  const [search, setSearch] = useState<AdSearch | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [currentImage, setCurrentImage] = useState(0)
  const [showReasoning, setShowReasoning] = useState(true)
  const [imgErrors, setImgErrors] = useState<Set<number>>(new Set())

  useEffect(() => {
    if (Number.isNaN(id)) return
    async function load() {
      setLoading(true)
      setError(null)
      try {
        const adData = await fetchAd(id)
        setAd(adData)
        try {
          const searchData = await fetchSearch(adData.adsearch_id)
          setSearch(searchData)
        } catch {
          setSearch(null)
        }
      } catch (e) {
        const msg = e instanceof Error ? e.message : "Anzeige konnte nicht geladen werden."
        setError(msg)
        toast.error(msg)
        setAd(null)
        setSearch(null)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [id])

  const images = useMemo(() => (ad ? getAdImageUrls(ad) : []), [ad])

  const goToPrevImage = useCallback(() => {
    setCurrentImage((prev) => (prev > 0 ? prev - 1 : images.length - 1))
  }, [images.length])

  const goToNextImage = useCallback(() => {
    setCurrentImage((prev) => (prev < images.length - 1 ? prev + 1 : 0))
  }, [images.length])

  useEffect(() => {
    if (images.length <= 1) return
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "ArrowLeft") goToPrevImage()
      if (e.key === "ArrowRight") goToNextImage()
    }
    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [images.length, goToPrevImage, goToNextImage])

  const touchStartX = useRef<number | null>(null)

  function handleTouchStart(e: React.TouchEvent) {
    touchStartX.current = e.touches[0].clientX
  }

  function handleTouchEnd(e: React.TouchEvent) {
    if (touchStartX.current === null) return
    const diff = e.changedTouches[0].clientX - touchStartX.current
    touchStartX.current = null
    if (Math.abs(diff) < 50) return
    if (diff < 0) goToNextImage()
    else goToPrevImage()
  }

  function handleImageError(index: number) {
    setImgErrors((prev) => new Set(prev).add(index))
  }

  if (loading) {
    return (
      <div className="flex flex-col gap-6">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-64" />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <Skeleton className="h-48 lg:col-span-2" />
          <Skeleton className="h-48" />
        </div>
      </div>
    )
  }

  if (error || !ad) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-4">
        <p className="text-muted-foreground">{error || "Anzeige nicht gefunden."}</p>
        <Button variant="outline" onClick={() => router.push("/ads")} className="cursor-pointer">
          Zurück zur Übersicht
        </Button>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6">
      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem>
            <BreadcrumbLink href="/">Start</BreadcrumbLink>
          </BreadcrumbItem>
          <BreadcrumbSeparator />
          <BreadcrumbItem>
            <BreadcrumbLink href="/ads">Anzeigen</BreadcrumbLink>
          </BreadcrumbItem>
          <BreadcrumbSeparator />
          <BreadcrumbItem>
            <BreadcrumbPage>{ad.title.length > 40 ? ad.title.slice(0, 40) + "..." : ad.title}</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>

      <div className="flex items-center gap-2">
        <Button variant="ghost" size="icon-sm" onClick={() => router.push("/ads")} className="cursor-pointer" aria-label="Zurück">
          <ArrowLeft className="size-4" />
        </Button>
        <div className="flex-1 flex items-center justify-between gap-4 flex-wrap">
          <h1 className="text-2xl font-bold tracking-tight text-foreground">{ad.title}</h1>
          <div className="flex items-center gap-2">
            <Button asChild variant="outline" size="sm" className="cursor-pointer">
              <a href={ad.url} target="_blank" rel="noopener noreferrer" aria-label="Auf Kleinanzeigen ansehen (neues Fenster)">
                <ExternalLinkIcon className="size-3.5" />
                Auf Kleinanzeigen ansehen
              </a>
            </Button>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Images + Description */}
        <div className="lg:col-span-2 flex flex-col gap-6">
          {/* Image Gallery */}
          <Card className="overflow-hidden p-0 card-lift">
            <div
              className="aspect-[16/10] relative bg-muted"
              onTouchStart={handleTouchStart}
              onTouchEnd={handleTouchEnd}
            >
              {images.length > 0 && !imgErrors.has(currentImage) ? (
                <Image
                  src={images[currentImage]}
                  alt={ad.title}
                  fill
                  className="object-contain"
                  unoptimized
                  onError={() => handleImageError(currentImage)}
                />
              ) : (
                <div className="absolute inset-0 flex flex-col items-center justify-center gap-2">
                  <Package className="size-16 text-muted-foreground/30" />
                  <span className="text-muted-foreground text-sm">
                    {imgErrors.has(currentImage) ? "Bild nicht verfügbar" : "Kein Bild verfügbar"}
                  </span>
                </div>
              )}
              {images.length > 1 && (
                <>
                  <Button
                    variant="secondary"
                    size="icon"
                    className="absolute left-2 top-1/2 -translate-y-1/2 z-10 cursor-pointer opacity-80 hover:opacity-100 transition-opacity"
                    onClick={goToPrevImage}
                    aria-label="Vorheriges Bild"
                  >
                    <ChevronLeft className="size-5" />
                  </Button>
                  <Button
                    variant="secondary"
                    size="icon"
                    className="absolute right-2 top-1/2 -translate-y-1/2 z-10 cursor-pointer opacity-80 hover:opacity-100 transition-opacity"
                    onClick={goToNextImage}
                    aria-label="Nächstes Bild"
                  >
                    <ChevronRight className="size-5" />
                  </Button>
                  <div className="absolute bottom-2 left-1/2 -translate-x-1/2 z-10 bg-black/50 text-white text-xs px-2 py-0.5 rounded-full">
                    {currentImage + 1} / {images.length}
                  </div>
                </>
              )}
            </div>
            {images.length > 1 && (
              <div className="flex gap-2 p-3 overflow-x-auto">
                {images.map((img, i) => (
                  <button
                    key={i}
                    onClick={() => setCurrentImage(i)}
                    className={`size-16 rounded-md overflow-hidden shrink-0 border-2 transition-colors cursor-pointer ${
                      i === currentImage ? "border-primary" : "border-transparent hover:border-muted-foreground/30"
                    }`}
                    aria-label={`Bild ${i + 1} von ${images.length}`}
                  >
                    {imgErrors.has(i) ? (
                      <div className="size-full bg-muted flex items-center justify-center">
                        <Package className="size-4 text-muted-foreground/30" />
                      </div>
                    ) : (
                      <Image
                        src={img}
                        alt={`Bild ${i + 1}`}
                        width={64}
                        height={64}
                        className="size-full object-cover"
                        unoptimized
                        onError={() => handleImageError(i)}
                      />
                    )}
                  </button>
                ))}
              </div>
            )}
          </Card>

          {/* Price + Details */}
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between mb-4">
                <span className="text-3xl font-bold text-foreground">{formatPrice(ad.price)}</span>
                {search && (
                  <Badge variant="secondary" className="text-xs cursor-default">
                    {search.name}
                  </Badge>
                )}
              </div>
              <div className="grid grid-cols-2 gap-4 pt-4 border-t">
                {ad.condition && (
                  <div>
                    <span className="text-xs text-muted-foreground uppercase tracking-wider">Zustand</span>
                    <p className="mt-1 text-foreground font-medium">{ad.condition}</p>
                  </div>
                )}
                {ad.shipping_cost && (
                  <div>
                    <span className="text-xs text-muted-foreground uppercase tracking-wider">Versandkosten</span>
                    <p className="mt-1 text-foreground font-medium">{ad.shipping_cost}</p>
                  </div>
                )}
                <div>
                  <span className="text-xs text-muted-foreground uppercase tracking-wider">Standort</span>
                  <p className="mt-1 text-foreground font-medium">{ad.postal_code} {ad.city}</p>
                </div>
                <div>
                  <span className="text-xs text-muted-foreground uppercase tracking-wider">Gefunden</span>
                  <p className="mt-1 text-foreground font-medium">{timeAgo(ad.first_seen_at)}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Description */}
          {ad.description && (
            <Card>
              <CardHeader>
                <CardTitle>Beschreibung</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-foreground whitespace-pre-wrap leading-relaxed">
                  {ad.description}
                </p>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Right: Seller + AI Analysis - Sticky */}
        <div className="flex flex-col gap-6">
          <div className="sticky-panel space-y-6">
            {/* Seller Box */}
            <Card>
              <CardHeader className="pb-4">
                <CardTitle className="flex items-center gap-2 text-base">
                  <User className="size-4" />
                  Verkäufer
                </CardTitle>
              </CardHeader>
              <CardContent className="flex flex-col gap-3">
                {ad.seller_name && (
                  <div>
                    {ad.seller_url ? (
                      <ExternalLink href={ad.seller_url}>{ad.seller_name}</ExternalLink>
                    ) : (
                      <span className="text-sm font-medium text-foreground">{ad.seller_name}</span>
                    )}
                  </div>
                )}
                <div className="flex flex-wrap gap-2">
                  <SellerRatingTag rating={ad.seller_rating} />
                  {ad.seller_is_friendly && (
                    <Badge variant="secondary" className="bg-emerald-50 text-emerald-700 border-emerald-200">
                      <ThumbsUp className="size-3" />
                      Freundlich
                    </Badge>
                  )}
                  {ad.seller_is_reliable && (
                    <Badge variant="secondary" className="bg-blue-50 text-blue-700 border-blue-200">
                      <ShieldCheck className="size-3" />
                      Zuverlässig
                    </Badge>
                  )}
                </div>
                <div className="text-xs text-muted-foreground space-y-1 pt-2 border-t">
                  {ad.seller_type && (
                    <div className="flex justify-between">
                      <span>Typ:</span>
                      <span className="text-foreground font-medium">{ad.seller_type}</span>
                    </div>
                  )}
                  {ad.seller_active_since && (
                    <div className="flex justify-between">
                      <span>Aktiv seit:</span>
                      <span className="text-foreground font-medium">{ad.seller_active_since}</span>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* AI Analysis - Enhanced sticky card */}
            <Card className="border-amber-200 bg-gradient-to-b from-amber-50/80 to-amber-50/50 shadow-md">
              <CardHeader className="pb-4">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-amber-900 text-base flex items-center gap-2">
                    <Sparkles className="size-4 text-amber-600" />
                    KI-Analyse
                  </CardTitle>
                  {ad.bargain_score !== null && ad.bargain_score !== undefined && (
                    <ScoreBadge score={ad.bargain_score} size="md" />
                  )}
                </div>
              </CardHeader>
              <CardContent className="flex flex-col gap-4">
                {ad.is_analyzed ? (
                  <>
                    {ad.ai_summary && (
                      <div className="p-3 rounded-lg bg-white/60 backdrop-blur-sm border border-amber-100">
                        <span className="text-xs text-amber-800 font-semibold uppercase tracking-wide">Zusammenfassung</span>
                        <p className="text-sm text-amber-900 mt-2 leading-relaxed">{ad.ai_summary}</p>
                      </div>
                    )}
                    {ad.ai_reasoning && (
                      <div>
                        <button
                          onClick={() => setShowReasoning(!showReasoning)}
                          className="flex items-center gap-1 text-xs text-amber-700 hover:text-amber-900 cursor-pointer font-medium transition-colors py-2"
                        >
                          {showReasoning ? <ChevronUp className="size-3.5" /> : <ChevronDown className="size-3.5" />}
                          Begründung {showReasoning ? "ausblenden" : "anzeigen"}
                        </button>
                        {showReasoning && (
                          <div className="p-3 rounded-lg bg-white/40 border border-amber-100">
                            <p className="text-sm text-amber-900 leading-relaxed">
                              {ad.ai_reasoning}
                            </p>
                          </div>
                        )}
                      </div>
                    )}
                  </>
                ) : (
                  <div className="flex flex-col items-center justify-center py-6 text-center">
                    <Package className="size-8 text-amber-400" />
                    <p className="text-sm text-amber-700 mt-2">Noch nicht analysiert</p>
                    <p className="text-xs text-amber-600 mt-1">
                      Diese Anzeige wird beim nächsten Durchlauf analysiert.
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  )
}
