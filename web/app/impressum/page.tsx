"use client"

import Link from "next/link"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

export default function ImpressumPage() {
  return (
    <main className="min-h-svh bg-gradient-to-b from-background to-muted/30">
      <div className="mx-auto flex min-h-svh w-full max-w-2xl flex-col justify-center gap-6 px-4 py-10">
        <Card>
          <CardHeader>
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

            <p className="text-muted-foreground">
              Weitere rechtliche Informationen findest du in der{" "}
              <Link href="/datenschutz" className="underline underline-offset-4 hover:text-foreground">
                Datenschutzerklärung
              </Link>
              .
            </p>
          </CardContent>
        </Card>
      </div>
    </main>
  )
}

