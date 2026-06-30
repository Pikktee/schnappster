"use client"

import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import type { PricePoint } from "@/lib/types"
import { formatPriceWithCurrency } from "@/lib/format"

interface PriceHistoryChartProps {
  points: PricePoint[]
  currency: string | null
  threshold?: number | null
}

interface ChartDatum {
  t: number
  price: number
}

function formatAxisDate(value: number, spanDays: number): string {
  const date = new Date(value)
  if (spanDays <= 2) {
    return date.toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" })
  }
  return date.toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit" })
}

interface TooltipPayload {
  payload: ChartDatum
}

function ChartTooltip({
  active,
  payload,
  currency,
}: {
  active?: boolean
  payload?: TooltipPayload[]
  currency: string | null
}) {
  if (!active || !payload?.length) return null
  const datum = payload[0].payload
  return (
    <div className="rounded-lg border border-border bg-popover px-3 py-2 text-xs shadow-md">
      <div className="font-semibold tabular-nums text-foreground">
        {formatPriceWithCurrency(datum.price, currency)}
      </div>
      <div className="mt-0.5 text-muted-foreground">
        {new Date(datum.t).toLocaleString("de-DE", {
          day: "2-digit",
          month: "2-digit",
          year: "numeric",
          hour: "2-digit",
          minute: "2-digit",
        })}
      </div>
    </div>
  )
}

export function PriceHistoryChart({ points, currency, threshold }: PriceHistoryChartProps) {
  if (points.length === 0) {
    return (
      <div className="flex h-[240px] items-center justify-center text-sm text-muted-foreground">
        Noch keine Preisdaten — der Verlauf erscheint nach der ersten Preisänderung.
      </div>
    )
  }

  const data: ChartDatum[] = points.map((p) => ({
    t: new Date(p.recorded_at).getTime(),
    price: p.price,
  }))

  const spanDays = (data[data.length - 1].t - data[0].t) / 86_400_000
  const prices = data.map((d) => d.price)
  if (threshold != null) prices.push(threshold)
  const min = Math.min(...prices)
  const max = Math.max(...prices)
  const pad = (max - min) * 0.12 || max * 0.05 || 1

  return (
    <ResponsiveContainer width="100%" height={240}>
      <LineChart data={data} margin={{ top: 8, right: 16, bottom: 4, left: 4 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
        <XAxis
          dataKey="t"
          type="number"
          scale="time"
          domain={["dataMin", "dataMax"]}
          tickFormatter={(v) => formatAxisDate(v, spanDays)}
          tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
          stroke="var(--border)"
          minTickGap={40}
        />
        <YAxis
          domain={[min - pad, max + pad]}
          tickFormatter={(v) => formatPriceWithCurrency(v, currency)}
          tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
          stroke="var(--border)"
          width={72}
        />
        <Tooltip content={<ChartTooltip currency={currency} />} />
        {threshold != null && (
          <ReferenceLine
            y={threshold}
            stroke="#10b981"
            strokeDasharray="5 4"
            label={{
              value: "Zielpreis",
              position: "insideTopRight",
              fontSize: 10,
              fill: "#10b981",
            }}
          />
        )}
        <Line
          type="stepAfter"
          dataKey="price"
          stroke="var(--primary)"
          strokeWidth={2.5}
          dot={{ r: 3, fill: "var(--primary)", strokeWidth: 0 }}
          activeDot={{ r: 5 }}
          isAnimationActive={false}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}
