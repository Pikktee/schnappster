"use client"

import { useCallback, useState } from "react"
import { Handshake, Copy, RefreshCw, Check, Lightbulb } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Spinner } from "@/components/ui/spinner"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { generateNegotiationMessage } from "@/lib/api"
import { formatPrice } from "@/lib/format"
import { toast } from "sonner"

interface NegotiationDialogProps {
  adId: number
}

/**
 * KI-Verhandlungsassistent (Stufe 1): erzeugt eine Nachricht + faires Gegenangebot,
 * die der Nutzer prüft, ggf. anpasst und selbst zu Kleinanzeigen kopiert.
 */
export function NegotiationDialog({ adId }: NegotiationDialogProps) {
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState("")
  const [offer, setOffer] = useState<number | null>(null)
  const [reasoning, setReasoning] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  const generate = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await generateNegotiationMessage(adId)
      setMessage(res.message)
      setOffer(res.suggested_offer)
      setReasoning(res.reasoning)
    } catch (e) {
      setError(e instanceof Error ? e.message : "Es konnte keine Nachricht erzeugt werden.")
    } finally {
      setLoading(false)
    }
  }, [adId])

  const handleOpenChange = useCallback(
    (next: boolean) => {
      setOpen(next)
      // Beim ersten Öffnen automatisch einen Entwurf erzeugen.
      if (next && !message && !loading) void generate()
    },
    [message, loading, generate]
  )

  async function copyMessage() {
    try {
      await navigator.clipboard.writeText(message)
      setCopied(true)
      toast.success("Nachricht kopiert")
      setTimeout(() => setCopied(false), 2000)
    } catch {
      toast.error("Kopieren fehlgeschlagen — bitte manuell markieren.")
    }
  }

  return (
    <>
      <Button
        variant="outline"
        className="w-full cursor-pointer"
        onClick={() => handleOpenChange(true)}
      >
        <Handshake className="size-4" aria-hidden />
        Verhandlungsnachricht entwerfen
      </Button>

      <Dialog open={open} onOpenChange={handleOpenChange}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Handshake className="size-5 text-primary" aria-hidden />
              Verhandlungsnachricht
            </DialogTitle>
            <DialogDescription>
              KI-Entwurf für deine Nachricht an den Verkäufer. Prüfe ihn, passe ihn an und
              kopiere ihn zu Kleinanzeigen.
            </DialogDescription>
          </DialogHeader>

          {loading ? (
            <div className="flex flex-col items-center gap-3 py-10 text-muted-foreground">
              <Spinner />
              <p className="text-sm">Entwurf wird erstellt…</p>
            </div>
          ) : error ? (
            <div className="flex flex-col items-center gap-3 py-8 text-center">
              <p className="text-sm text-destructive">{error}</p>
              <Button variant="outline" onClick={generate} className="cursor-pointer">
                <RefreshCw className="size-4" aria-hidden />
                Erneut versuchen
              </Button>
            </div>
          ) : (
            <div className="flex flex-col gap-3">
              {offer !== null && (
                <div className="flex items-center gap-2 rounded-lg bg-primary/10 px-3 py-2 text-sm ring-1 ring-primary/15">
                  <span className="text-muted-foreground">Vorgeschlagenes Gebot:</span>
                  <span className="font-semibold text-foreground">{formatPrice(offer)}</span>
                </div>
              )}
              <Textarea
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                rows={7}
                className="resize-none leading-relaxed"
                aria-label="Verhandlungsnachricht"
              />
              {reasoning && (
                <p className="flex items-start gap-1.5 text-xs text-muted-foreground">
                  <Lightbulb className="size-3.5 shrink-0 mt-0.5" aria-hidden />
                  <span>{reasoning}</span>
                </p>
              )}
              <div className="flex items-center justify-between gap-2 pt-1">
                <Button variant="ghost" size="sm" onClick={generate} className="cursor-pointer">
                  <RefreshCw className="size-4" aria-hidden />
                  Neu generieren
                </Button>
                <Button onClick={copyMessage} disabled={!message} className="cursor-pointer">
                  {copied ? <Check className="size-4" aria-hidden /> : <Copy className="size-4" aria-hidden />}
                  {copied ? "Kopiert" : "Kopieren"}
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </>
  )
}
