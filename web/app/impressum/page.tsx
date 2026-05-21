"use client"

import Image from "next/image"
import Link from "next/link"
import { ArrowLeft } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

export default function ImpressumPage() {
  return (
    <main className="min-h-svh bg-gradient-to-b from-background to-muted/30">
      <div className="mx-auto flex min-h-svh w-full max-w-2xl flex-col justify-center gap-6 px-4 py-10">
        <Button variant="ghost" size="sm" className="w-fit gap-2" asChild>
          <Link href="/">
            <ArrowLeft className="size-4" />
            Zurück
          </Link>
        </Button>
        <Card>
          <CardHeader className="space-y-4">
            <div className="flex items-center gap-3">
              <Image
                src="/icon.png"
                alt="Schnappster Logo"
                width={32}
                height={32}
                className="rounded-md"
              />
              <p className="text-sm text-muted-foreground">Schnappster</p>
            </div>
            <CardTitle>Impressum</CardTitle>
          </CardHeader>
          <CardContent className="space-y-5 text-sm leading-relaxed">
            <div>
              <p className="font-medium">Angaben gemäß § 5 TMG</p>
              <p className="mt-2 whitespace-pre-line">
                {`Henrik Heil
Westendstr. 100
60325 Frankfurt`}
              </p>
            </div>
            <div>
              <p className="font-medium">Kontakt</p>
              <p className="mt-2">
                E-Mail:{" "}
                <a className="underline underline-offset-4" href="mailto:contact@henrikheil.net">
                  contact@henrikheil.net
                </a>
              </p>
            </div>

            <div>
              <p className="font-medium">Datenschutz</p>
              <p className="mt-2 text-muted-foreground">
                Informationen zur Verarbeitung personenbezogener Daten findest du in unserer{" "}
                <Link href="/datenschutz" className="underline underline-offset-4 hover:text-foreground">
                  Datenschutzerklärung
                </Link>
                .
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    </main>
  )
}

