import { AdDetailPage } from "./ad-detail-page"

export function generateStaticParams() {
  return [{ id: "0" }]
}

export default function Page() {
  return <AdDetailPage />
}
