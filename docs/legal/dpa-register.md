# DPA-/AVV-Register (Schnappster)

Stand: 2026-04-08

## Zweck

Dieses Register dokumentiert den Status von Auftragsverarbeitungsvertraegen (DPA/AVV)
mit externen Dienstleistern.

## Register

| Dienst | Leistungsbereich | DPA/AVV Status | Beantragt am | Abgeschlossen am | Ablageort | Naechste Aktion |
| --- | --- | --- | --- | --- | --- | --- |
| Supabase | Datenbank, Auth, ggf. Storage | Beantragt | 2026-04-08 | Offen | (eintragen, z. B. verschluesselter Ordner) | Status in 24h pruefen, Abschluss dokumentieren |
| Hosting-Provider (offen) | App-Betrieb Production | Offen | Offen | Offen | Offen | Provider festlegen und DPA initiieren |
| Monitoring/Logging (offen) | Betriebsueberwachung, Fehleranalyse | Offen | Offen | Offen | Offen | Toolwahl treffen, dann DPA pruefen |
| E-Mail-Provider (offen) | Transaktionale E-Mails (optional) | Offen | Offen | Offen | Offen | Bei Einfuehrung DPA pruefen/abschliessen |

## Pflege-Regeln

- Bei jedem neuen externen Tool sofort pruefen, ob ein DPA/AVV erforderlich ist.
- Nach Vertragsabschluss Datum und Ablageort zeitnah nachtragen.
- Vor Production-Start duerfen fuer aktive produktive Dienste keine `Offen`-Eintraege verbleiben.

## Kurz-Check vor Go-Live

- [ ] Supabase DPA auf `Abgeschlossen` gesetzt
- [ ] Hosting-DPA vorhanden
- [ ] Monitoring/Logging-DPA geklaert (falls aktiv)
- [ ] E-Mail-DPA geklaert (falls aktiv)
