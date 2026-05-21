"use client"

import type { ReactNode } from "react"
import Link from "next/link"
import { motion } from "motion/react"
import {
  Gauge,
  TrendingDown,
  Radar,
  Bell,
  ArrowRight,
  Check,
} from "lucide-react"
import { Owl } from "./Owl"
import { DashboardPreview } from "./DashboardPreview"
import { Reveal } from "./Reveal"
import { ParticleField } from "./ParticleField"

const cream = "#FAFAF9"
const ink = "#1C1917"

const HEADER_OFFSET = 64

function scrollToId(id: string) {
  const el = document.getElementById(id)
  if (!el) return
  const top = el.getBoundingClientRect().top + window.scrollY - HEADER_OFFSET
  window.scrollTo({ top, behavior: "smooth" })
}

function NavLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <a
      href={href}
      onClick={(e) => {
        e.preventDefault()
        scrollToId(href.slice(1))
      }}
      className="group relative text-[#57534E] hover:text-[#1C1917] transition-colors duration-150 ease-out"
    >
      {children}
      <span
        aria-hidden
        className="pointer-events-none absolute left-0 -bottom-1 h-[1.5px] w-full origin-left scale-x-0 bg-[#F59E0B] transition-transform duration-150 ease-out group-hover:scale-x-100"
      />
    </a>
  )
}

function Nav() {
  return (
    <header className="sticky top-0 z-30 backdrop-blur-md bg-[#FAFAF9]/75 border-b border-stone-200/60">
      <div className="max-w-6xl mx-auto px-6 py-3 flex items-center justify-between">
        <a href="#top" className="flex items-center gap-2.5 leading-none">
          <span className="flex items-center justify-center" style={{ width: 36, height: 36 }}>
            <Owl size={36} />
          </span>
          <span
            style={{
              fontFamily: "'Fredoka', 'Baloo 2', 'Poppins', system-ui, sans-serif",
              fontWeight: 400,
              fontSize: "1.25rem",
              lineHeight: 1,
              letterSpacing: "-0.015em",
              color: "#1C1917",
              display: "inline-block",
              transform: "translateY(0.5px)",
            }}
          >
            Schnapp<span style={{ color: "#D97706" }}>ster</span>
          </span>
        </a>
        <nav className="hidden md:flex items-center gap-8 text-sm text-stone-600">
          <NavLink href="#how">So funktioniert&apos;s</NavLink>
          <NavLink href="#features">Funktionen</NavLink>
          <NavLink href="#dashboard">Dashboard</NavLink>
        </nav>
        <Link
          href="/register"
          className="px-4 py-2 rounded-full bg-amber-500 hover:bg-amber-600 text-white text-sm transition-colors shadow-sm"
        >
          Loslegen
        </Link>
      </div>
    </header>
  )
}

function Hero() {
  return (
    <section id="top" className="relative overflow-hidden">
      {/* Background container for hero animation */}
      <div id="hero-bg" aria-hidden className="absolute inset-0 z-0">
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute -top-32 -left-32 w-[520px] h-[520px] rounded-full bg-amber-200/40 blur-3xl" />
          <div className="absolute top-40 -right-32 w-[460px] h-[460px] rounded-full bg-emerald-200/30 blur-3xl" />
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_120%,rgba(245,158,11,0.10),transparent_60%)]" />
        </div>
        <ParticleField />
        {/* Soft left-side veil so the headline stays readable */}
        <div className="absolute inset-y-0 left-0 w-2/3 pointer-events-none bg-gradient-to-r from-[#FAFAF9] via-[#FAFAF9]/70 to-transparent" />
      </div>

      <div className="relative z-10 max-w-6xl mx-auto px-6 pt-14 pb-20 md:pt-20 md:pb-24">
        <div className="grid lg:grid-cols-12 gap-10 items-center">
          <div className="lg:col-span-7">
            <Reveal>
              <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-amber-100 text-amber-700 text-sm mx-[0px] mt-[0px] mb-[8px]">
                Deine KI-Eule für Kleinanzeigen
              </div>
            </Reveal>
            <Reveal delay={0.05}>
              <h1 className="text-4xl md:text-6xl leading-[1.05] tracking-tight text-stone-900 mb-6">
                Schnapp dir das beste Angebot,{" "}
                <span className="relative inline-block">
                  <span className="relative z-10 mx-[0px] my-[4px]">bevor es weg ist.</span>
                  <span className="absolute left-0 right-0 bottom-1 h-3 bg-amber-200/70 -z-0 rounded-sm" />
                </span>
              </h1>
            </Reveal>
            <Reveal delay={0.12}>
              <p className="text-lg text-stone-600 max-w-xl mx-[0px] mt-[0px] mb-[32px] px-[0px] py-[8px] pt-[8px] pb-[0px]">
                Unsere KI-Eule fliegt 24/7 durch Kleinanzeigen, bewertet jedes
                Inserat und ruft nur, wenn sich wirklich ein Schnäppchen lohnt.
                Du lehnst dich zurück — sie jagt.
              </p>
            </Reveal>
            <Reveal delay={0.18}>
              <div className="flex flex-wrap items-center gap-3">
                <Link
                  href="/register"
                  className="group inline-flex items-center gap-2 px-6 py-3.5 rounded-full bg-amber-500 hover:bg-amber-600 text-white shadow-[0_10px_30px_-10px_rgba(245,158,11,0.6)] transition-all hover:-translate-y-0.5"
                >
                  Jetzt Schnäppchen jagen
                  <ArrowRight size={18} className="group-hover:translate-x-0.5 transition-transform" />
                </Link>
                <a
                  href="#how"
                  className="inline-flex items-center gap-2 px-6 py-3.5 rounded-full bg-white border border-stone-200 hover:border-stone-300 text-stone-800 transition-colors"
                >
                  So funktioniert&apos;s
                </a>
              </div>
            </Reveal>
            <Reveal delay={0.25}>
              <div className="mt-8 flex items-center gap-6 text-sm text-stone-500">
                <div className="flex items-center gap-2"><Check size={16} className="text-emerald-500" /> Kostenlos testen</div>
                <div className="flex items-center gap-2"><Check size={16} className="text-emerald-500" /> Keine Kreditkarte</div>
              </div>
            </Reveal>
          </div>

          <div className="lg:col-span-5 flex justify-center lg:justify-end">
            <Reveal delay={0.1} y={32}>
              <div className="relative">
                <div className="absolute inset-0 blur-3xl bg-amber-300/30 rounded-full scale-90" />
                <Owl
                  size={520}
                  className="relative drop-shadow-xl w-[340px] sm:w-[420px] lg:w-[520px] h-auto max-w-full -translate-y-5"
                />
              </div>
            </Reveal>
          </div>
        </div>
      </div>
    </section>
  )
}

function ProblemSolution() {
  return (
    <section className="py-14 md:py-20 border-y border-stone-200/70 bg-white/50">
      <div className="max-w-4xl mx-auto px-6 text-center">
        <Reveal>
          <h2 className="text-3xl md:text-5xl tracking-tight text-stone-900 mb-5">
            Stundenlang Kleinanzeigen durchscrollen?{" "}
            <span className="text-amber-600">Macht die Eule für dich.</span>
          </h2>
        </Reveal>
        <Reveal delay={0.1}>
          <p className="text-lg text-stone-600 leading-relaxed">
            Refresh, refresh, refresh — und das gute Angebot ist trotzdem weg.
            Schnappster scannt rund um die Uhr neue Inserate, vergleicht Preise
            mit echten Marktdaten und meldet sich nur, wenn ein Deal wirklich
            ein Deal ist. Nie wieder „zu spät“.
          </p>
        </Reveal>
      </div>
    </section>
  )
}

function HowItWorks() {
  const steps = [
    {
      title: "Suche anlegen",
      text: "Sag der Eule, wonach du jagst — Kategorie, Ort, Preisrahmen, Stichwörter.",
    },
    {
      title: "KI bewertet das Angebot",
      text: "Jedes neue Inserat wird in Sekunden mit Marktpreisen verglichen und benotet.",
    },
    {
      title: "Schnäppchen landen im Dashboard",
      text: "Nur die echten Treffer — sortiert nach Bargain-Score, sofort einsatzbereit.",
    },
  ]
  return (
    <section id="how" className="py-16 md:py-20">
      <div className="max-w-6xl mx-auto px-6">
        <div className="text-center mb-12">
          <Reveal>
            <div className="text-sm text-amber-600 mb-3 tracking-wide uppercase">So funktioniert&apos;s</div>
          </Reveal>
          <Reveal delay={0.05}>
            <h2 className="text-3xl md:text-5xl tracking-tight text-stone-900">
              In drei Schritten zum Schnäppchen
            </h2>
          </Reveal>
        </div>
        <div className="grid md:grid-cols-3 gap-6 relative">
          {steps.map((s, i) => (
            <Reveal key={s.title} delay={i * 0.1}>
              <div className="group relative h-full rounded-2xl bg-white border border-stone-200/80 p-8 pt-10 shadow-[0_1px_2px_rgba(28,25,23,0.04)] hover:shadow-[0_4px_12px_-6px_rgba(28,25,23,0.08)] hover:border-stone-300/80 hover:-translate-y-0.5 transition-all duration-300">
                <div className="absolute -top-5 left-8 w-10 h-10 rounded-full bg-amber-500 text-white flex items-center justify-center shadow-md">
                  {i + 1}
                </div>
                <h3 className="text-xl text-stone-900 mb-3 mt-2">{s.title}</h3>
                <p className="text-stone-600 leading-relaxed">{s.text}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  )
}

function Features() {
  const features = [
    {
      icon: Gauge,
      title: "Bargain-Score 0–10",
      text: "Eine einzige Zahl sagt dir, wie gut der Deal wirklich ist — kalibriert auf echten Marktdaten.",
    },
    {
      icon: TrendingDown,
      title: "Automatischer Preisvergleich",
      text: "Die Eule kennt vergleichbare Verkäufe und erkennt sofort, ob der Preis unterm Schnitt liegt.",
    },
    {
      icon: Radar,
      title: "24/7 Scraping",
      text: "Während du schläfst, jagt sie weiter. Neue Inserate werden in Sekunden geprüft.",
    },
    {
      icon: Bell,
      title: "Telegram-Benachrichtigungen",
      text: "Top-Treffer landen direkt auf deinem Handy — mit Bild, Score und Direktlink.",
    },
  ]
  return (
    <section id="features" className="py-16 md:py-20 bg-gradient-to-b from-transparent to-amber-50/40">
      <div className="max-w-6xl mx-auto px-6">
        <div className="text-center mb-12">
          <Reveal>
            <div className="text-sm text-amber-600 mb-3 tracking-wide uppercase">Funktionen</div>
          </Reveal>
          <Reveal delay={0.05}>
            <h2 className="text-3xl md:text-5xl tracking-tight text-stone-900 mb-4">
              Alles, was eine gute Jagd-Eule braucht
            </h2>
          </Reveal>
          <Reveal delay={0.1}>
            <p className="text-lg text-stone-600 max-w-2xl mx-auto">
              Keine Plugins, keine Tabellen-Bastelei. Schnappster macht aus
              Kleinanzeigen-Chaos eine saubere Trefferliste.
            </p>
          </Reveal>
        </div>
        <div className="grid sm:grid-cols-2 gap-5">
          {features.map((f, i) => {
            return (
              <Reveal key={f.title} delay={i * 0.08}>
                <div className="group h-full rounded-2xl bg-white border border-stone-200/80 p-7 shadow-[0_1px_2px_rgba(28,25,23,0.04)] hover:shadow-[0_4px_12px_-6px_rgba(28,25,23,0.08)] hover:border-stone-300/80 hover:-translate-y-0.5 transition-all duration-300">
                  <div
                    className="flex items-center justify-center mb-5 transition-transform duration-300 group-hover:-translate-y-0.5"
                    style={{
                      width: 48,
                      height: 48,
                      borderRadius: 14,
                      background: "linear-gradient(135deg, #F59E0B 0%, #D97706 100%)",
                      color: "#FFFFFF",
                      boxShadow:
                        "0 6px 14px -6px rgba(245,158,11,0.55), inset 0 1px 0 rgba(255,255,255,0.25)",
                    }}
                  >
                    <f.icon size={24} strokeWidth={2.25} absoluteStrokeWidth />
                  </div>
                  <h3 className="text-xl text-stone-900 mb-2">{f.title}</h3>
                  <p className="text-stone-600 leading-relaxed">{f.text}</p>
                </div>
              </Reveal>
            )
          })}
        </div>
      </div>
    </section>
  )
}

function DashboardSection() {
  return (
    <section id="dashboard" className="py-16 md:py-20">
      <div className="max-w-6xl mx-auto px-6">
        <div className="text-center mb-10">
          <Reveal>
            <div className="text-sm text-amber-600 mb-3 tracking-wide uppercase">Dein Cockpit</div>
          </Reveal>
          <Reveal delay={0.05}>
            <h2 className="text-3xl md:text-5xl tracking-tight text-stone-900 mb-4">
              Alle Schnäppchen auf einen Blick
            </h2>
          </Reveal>
          <Reveal delay={0.1}>
            <p className="text-lg text-stone-600 max-w-2xl mx-auto">
              Live-Scans, Score-Badges und die besten Treffer ganz oben — so
              klar war Sparen noch nie.
            </p>
          </Reveal>
        </div>
        <Reveal delay={0.1} y={40}>
          <DashboardPreview />
        </Reveal>
      </div>
    </section>
  )
}

function FooterCTA() {
  return (
    <section id="cta" className="relative py-16 md:py-20 overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-br from-amber-100 via-amber-50 to-emerald-50" />
      <div className="absolute -top-20 left-1/4 w-96 h-96 rounded-full bg-amber-200/40 blur-3xl" />
      <div className="absolute bottom-0 right-1/4 w-96 h-96 rounded-full bg-emerald-200/30 blur-3xl" />

      <div className="relative max-w-4xl mx-auto px-6 text-center">
        <Reveal>
          <motion.div
            animate={{ rotate: [0, -4, 4, -2, 0] }}
            transition={{ duration: 3.5, repeat: Infinity, ease: "easeInOut" }}
            className="inline-block mb-6"
          >
            <Owl size={160} />
          </motion.div>
        </Reveal>
        <Reveal delay={0.05}>
          <h2 className="text-4xl md:text-6xl tracking-tight text-stone-900 mb-5">
            Bereit für die Jagd?
          </h2>
        </Reveal>
        <Reveal delay={0.1}>
          <p className="text-lg text-stone-600 max-w-xl mx-auto mb-9">
            Leg in zwei Minuten deine erste Suche an. Die Eule kümmert sich um
            den Rest — versprochen.
          </p>
        </Reveal>
        <Reveal delay={0.15}>
          <Link
            href="/register"
            className="group inline-flex items-center gap-2 px-7 py-4 rounded-full bg-stone-900 hover:bg-stone-800 text-white shadow-[0_15px_40px_-15px_rgba(28,25,23,0.6)] transition-all hover:-translate-y-0.5"
          >
            Kostenlos Schnäppchen jagen
            <ArrowRight size={18} className="group-hover:translate-x-0.5 transition-transform" />
          </Link>
        </Reveal>
        <Reveal delay={0.2}>
          <div className="mt-6 text-sm text-stone-500">
            Hu-hu. Kein Spam, nur Schnapper.
          </div>
        </Reveal>
      </div>
    </section>
  )
}

function Footer() {
  return (
    <footer className="border-t border-stone-200/70 py-10">
      <div className="max-w-6xl mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-4 text-sm text-stone-500">
        <div className="flex items-center gap-2">
          <Owl size={28} />
          <span>© {new Date().getFullYear()} Schnappster. Mit Eulen-Flügeln gebaut.</span>
        </div>
        <div className="flex items-center gap-6">
          <Link href="/datenschutz" className="hover:text-stone-900">Datenschutz</Link>
          <Link href="/impressum" className="hover:text-stone-900">Impressum</Link>
        </div>
      </div>
    </footer>
  )
}

export function LandingPage() {
  return (
    <div
      className="min-h-screen w-full scroll-smooth"
      style={{ background: cream, color: ink, fontFamily: "Lexend, system-ui, sans-serif" }}
    >
      <Nav />
      <main>
        <Hero />
        <ProblemSolution />
        <HowItWorks />
        <Features />
        <DashboardSection />
        <FooterCTA />
      </main>
      <Footer />
    </div>
  )
}
