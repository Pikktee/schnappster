import { AdDetailPage } from "./ad-detail-page"

export const dynamicParams = false

export function generateStaticParams() {
  return [{ id: "0" }]
}

export default function Page() {
  return <AdDetailPage />
}
