"use client"

import { usePathname } from "next/navigation"
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"
import { PageHeader } from "@/components/page-header"
import { usePageHead } from "./page-head-context"

export function AppPageHead() {
  const pathname = usePathname()
  const { title, subtitle, headerActions, titleSuffix } = usePageHead()

  const pathSegments = pathname.split("/").filter(Boolean)
  const lastSegment = pathSegments[pathSegments.length - 1] ?? ""
  const isDetail = pathSegments.length >= 2 && /^\d+$/.test(lastSegment)
  // Anlegen-/Bearbeiten-Seiten führen den (gesetzten) Titel als letzte Breadcrumb-Stufe.
  const isForm = lastSegment === "new" || lastSegment === "edit"

  return (
    <div className="flex flex-col gap-6">
      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem>
            {pathname === "/dashboard" ? (
              <BreadcrumbPage>Start</BreadcrumbPage>
            ) : (
              <BreadcrumbLink href="/dashboard">Start</BreadcrumbLink>
            )}
          </BreadcrumbItem>
          {pathSegments.length >= 1 && pathSegments[0] === "ads" && (
            <>
              <BreadcrumbSeparator />
              <BreadcrumbItem>
                {/* Die Angebote-Liste ist im Start-Stream aufgegangen — zurück geht es dorthin. */}
                <BreadcrumbLink href="/dashboard">Angebote</BreadcrumbLink>
              </BreadcrumbItem>
            </>
          )}
          {pathSegments.length >= 1 && pathSegments[0] === "searches" && (
            <>
              <BreadcrumbSeparator />
              <BreadcrumbItem>
                {pathSegments.length === 1 ? (
                  <BreadcrumbPage>Suchaufträge</BreadcrumbPage>
                ) : (
                  <BreadcrumbLink href="/searches">Suchaufträge</BreadcrumbLink>
                )}
              </BreadcrumbItem>
            </>
          )}
          {pathSegments.length >= 1 && pathSegments[0] === "price-alerts" && (
            <>
              <BreadcrumbSeparator />
              <BreadcrumbItem>
                {pathSegments.length === 1 ? (
                  <BreadcrumbPage>Preis-Alarme</BreadcrumbPage>
                ) : (
                  <BreadcrumbLink href="/price-alerts">Preis-Alarme</BreadcrumbLink>
                )}
              </BreadcrumbItem>
            </>
          )}
          {pathSegments.length >= 1 && pathSegments[0] === "settings" && (
            <>
              <BreadcrumbSeparator />
              <BreadcrumbItem>
                <BreadcrumbPage>Einstellungen</BreadcrumbPage>
              </BreadcrumbItem>
            </>
          )}
          {pathSegments.length >= 1 && pathSegments[0] === "logs" && (
            <>
              <BreadcrumbSeparator />
              <BreadcrumbItem>
                <BreadcrumbPage>Logs</BreadcrumbPage>
              </BreadcrumbItem>
            </>
          )}
          {(isDetail || isForm) && (
            <>
              <BreadcrumbSeparator />
              <BreadcrumbItem>
                <BreadcrumbPage>
                  {title.length > 40 ? title.slice(0, 40) + "…" : title}
                </BreadcrumbPage>
              </BreadcrumbItem>
            </>
          )}
        </BreadcrumbList>
      </Breadcrumb>
      <PageHeader title={title} subtitle={subtitle || undefined} titleSuffix={titleSuffix}>
        {headerActions}
      </PageHeader>
    </div>
  )
}
