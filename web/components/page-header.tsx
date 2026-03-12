interface PageHeaderProps {
  title: string
  subtitle?: string
  titleSuffix?: React.ReactNode
  children?: React.ReactNode
}

export function PageHeader({ title, subtitle, titleSuffix, children }: PageHeaderProps) {
  return (
    <div className="flex items-start justify-between gap-4">
      <div className="flex flex-col gap-1">
        <div className="flex items-center gap-2 flex-wrap">
          <h1 className="text-2xl font-bold tracking-tight text-foreground text-balance">{title}</h1>
          {titleSuffix}
        </div>
        {subtitle && <p className="text-sm text-muted-foreground">{subtitle}</p>}
      </div>
      {children && <div className="flex items-center gap-2 shrink-0">{children}</div>}
    </div>
  )
}
