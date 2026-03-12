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
  const isDetail =
    pathSegments.length >= 2 &&
    /^\d+$/.test(pathSegments[pathSegments.length - 1] ?? "")

  return (
    <div className="flex flex-col gap-6">
      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem>
            {pathname === "/" || pathname === "" ? (
              <BreadcrumbPage>Start</BreadcrumbPage>
            ) : (
              <BreadcrumbLink href="/">Start</BreadcrumbLink>
            )}
          </BreadcrumbItem>
          {pathSegments.length >= 1 && pathSegments[0] === "ads" && (
            <>
              <BreadcrumbSeparator />
              <BreadcrumbItem>
                {pathSegments.length === 1 ? (
                  <BreadcrumbPage>Angebote</BreadcrumbPage>
                ) : (
                  <BreadcrumbLink href="/ads">Angebote</BreadcrumbLink>
                )}
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
          {isDetail && (
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
