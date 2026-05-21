import { TrendingDown, Search, Bell, Eye } from "lucide-react"

const deals = [
  {
    title: "Sony WH-1000XM5 Kopfhörer",
    price: "189 €",
    market: "349 €",
    score: 9.4,
    location: "Berlin",
    img: "https://images.unsplash.com/photo-1594916973877-0ce410768437?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=240",
    alt: "Over-ear headphones",
  },
  {
    title: "IKEA Markus Bürostuhl",
    price: "75 €",
    market: "229 €",
    score: 8.8,
    location: "München",
    img: "https://images.unsplash.com/photo-1713968686455-1af80cfd7b58?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=240",
    alt: "Black office chair",
  },
  {
    title: "Vintage Eames Lounge Chair",
    price: "420 €",
    market: "1.200 €",
    score: 9.7,
    location: "Hamburg",
    img: "https://images.unsplash.com/photo-1768687983413-adacbda44369?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=240",
    alt: "Mid-century leather lounge chair",
  },
  {
    title: "Canon EOS R6 + 24-105mm",
    price: "1.650 €",
    market: "2.400 €",
    score: 8.1,
    location: "Köln",
    img: "https://images.unsplash.com/photo-1611980834980-235b5cc709c8?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=240",
    alt: "Mirrorless camera with lens",
  },
  {
    title: "Lego Star Wars Millennium Falcon",
    price: "560 €",
    market: "850 €",
    score: 7.6,
    location: "Leipzig",
    img: "https://images.unsplash.com/photo-1637063868743-71757b4770c3?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=240",
    alt: "Lego brick set",
  },
]

const stats = [
  { label: "Aktive Suchen", value: "12", icon: Search },
  { label: "Schnäppchen heute", value: "37", icon: TrendingDown },
  { label: "Beobachtet", value: "184", icon: Eye },
  { label: "Benachrichtigungen", value: "8", icon: Bell },
]

export function DashboardPreview() {
  return (
    <div className="rounded-2xl bg-white shadow-[0_20px_60px_-20px_rgba(28,25,23,0.18)] border border-stone-200/70 overflow-hidden">
      {/* Top bar */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-stone-100 bg-stone-50/60">
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-full bg-red-300" />
          <span className="w-3 h-3 rounded-full bg-amber-300" />
          <span className="w-3 h-3 rounded-full bg-emerald-300" />
        </div>
        <div className="text-sm text-stone-500">schnappster.app / dashboard</div>
        <div className="w-12" />
      </div>

      <div className="p-6 md:p-8">
        <div className="flex items-end justify-between mb-6">
          <div>
            <div className="text-sm text-stone-500">Willkommen zurück</div>
            <div className="text-2xl text-stone-900">Deine Schnäppchen-Übersicht</div>
          </div>
          <div className="hidden sm:flex items-center gap-2 px-3 py-2 rounded-full bg-amber-50 text-amber-700 text-sm">
            <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
            Live-Scan aktiv
          </div>
        </div>

        {/* Stat cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {stats.map((s) => (
            <div key={s.label} className="rounded-xl border border-stone-200 bg-white p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="w-9 h-9 rounded-lg bg-amber-100 text-amber-600 flex items-center justify-center">
                  <s.icon size={18} />
                </div>
              </div>
              <div className="text-2xl text-stone-900">{s.value}</div>
              <div className="text-sm text-stone-500">{s.label}</div>
            </div>
          ))}
        </div>

        {/* Deals list */}
        <div className="flex items-center justify-between mb-4">
          <div className="text-lg text-stone-900">Letzte Schnäppchen</div>
          <button className="text-sm text-amber-600 hover:text-amber-700">Alle ansehen →</button>
        </div>
        <div className="space-y-2">
          {deals.map((d) => {
            const saving = Math.round(
              ((parseFloat(d.market.replace(/[^\d,]/g, "").replace(",", ".")) -
                parseFloat(d.price.replace(/[^\d,]/g, "").replace(",", "."))) /
                parseFloat(d.market.replace(/[^\d,]/g, "").replace(",", "."))) *
                100,
            )
            return (
              <div
                key={d.title}
                className="flex items-center gap-4 p-3 rounded-xl border border-stone-100 hover:border-amber-200 hover:bg-amber-50/40 transition-colors"
              >
                {/* eslint-disable-next-line @next/next/no-img-element -- external Unsplash preview thumbnails */}
                <img
                  src={d.img}
                  alt={d.alt}
                  loading="lazy"
                  className="w-12 h-12 rounded-[10px] object-cover flex-shrink-0 bg-stone-100"
                />
                <div className="flex-1 min-w-0">
                  <div className="truncate text-stone-900">{d.title}</div>
                  <div className="text-sm text-stone-500">{d.location} · Marktpreis {d.market}</div>
                </div>
                <div className="hidden md:block text-right">
                  <div className="text-stone-900">{d.price}</div>
                  <div className="text-sm text-emerald-600">−{saving}%</div>
                </div>
                <div className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-emerald-50 text-emerald-700 border border-emerald-100">
                  <span className="text-sm">★</span>
                  <span>{d.score.toFixed(1)}</span>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
