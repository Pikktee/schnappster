# Auth E-Mails im Schnappster-Style (Supabase)

Diese App nutzt fuer Registrierung und Passwort-Reset `supabase.auth`.  
Das heisst: Inhalt, Betreff und Absender der E-Mails werden in Supabase Auth gepflegt.

## 1) Branding und HTML-Templates

In Supabase Dashboard:

- `Authentication` -> `Email Templates`
- Pro Mailtyp Betreff und HTML setzen:
  - Confirm signup
  - Reset password
  - Invite user (optional)
  - Change email / Notifications (optional)

Vorlagen in diesem Repo:

- `docs/email-templates/confirm-signup.html`
- `docs/email-templates/reset-password.html`
- `docs/email-templates/invite-user.html`

Wichtige Platzhalter (Supabase):

- `{{ .ConfirmationURL }}`
- `{{ .SiteURL }}`
- `{{ .Email }}`

## 2) Logo in E-Mails

Supabase rendert HTML, aber das Logo muss als oeffentlich erreichbare URL eingebunden sein
(kein lokaler Dateipfad).

Beispiel:

- `https://app.schnappster.de/logo.png`

Im Template ist dafuer aktuell ein Platzhalter gesetzt:

- `https://app.schnappster.de/logo.png`

## 3) Versand ueber eigene Domain statt Supabase-Standard

Ja, das geht und ist fuer Produktion empfohlen.

- Standard-Supabase-Mailservice: nur fuer Dev/Test (niedrige Limits, best effort)
- Produktion: eigenes SMTP (z. B. Resend, Postmark, SES, SendGrid)

In Supabase Dashboard:

- `Authentication` -> `Providers` -> `Email` -> `Use custom SMTP`

Typische Felder:

- SMTP Host / Port / User / Password
- `From` Adresse, z. B. `no-reply@schnappster.de`
- Sendername, z. B. `Schnappster`

Danach bitte DNS sauber setzen:

- SPF
- DKIM
- optional DMARC

Nur so landen Mails stabil im Posteingang.

## 4) Optional per API konfigurieren

Geht auch ueber die Supabase Management API (`PATCH /v1/projects/{project_ref}/config/auth`)
fuer SMTP und Mail-Templates.
