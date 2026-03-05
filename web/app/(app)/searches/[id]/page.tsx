import { SearchDetailPage } from "./search-detail-page"

export function generateStaticParams() {
  return [{ id: "0" }]
}

export default function Page() {
  return <SearchDetailPage />
}
