# 03 - Benutzerprofil und Benachrichtigungen

## Ziel

Pro-User Profildaten und Benachrichtigungseinstellungen sauber trennen.

## Benutzerprofil

- Name: initial aus OAuth, editierbar
- Avatar: aus Supabase-User-Objekt im Frontend (`user.user_metadata.avatar_url`), kein DB-Feld, kein Upload/Storage
- E-Mail: aus Supabase Auth, read-only
- API-Scope: `/users/me` PATCH aendert nur den Namen (`display_name`), nicht Avatar/E-Mail

## Benachrichtigungskanaele

- Telegram: Bot-Token global in `.env`, Chat-ID pro User
- E-Mail (an Auth-E-Mail)

## Benachrichtigungsoptionen

- Kanal-Auswahl (Mehrfachauswahl)
- Mindest-Score (`bargain_score` 0-10)
- Modus: `instant` oder `daily_summary`

## Datenmodell: UserSettings

- `user_id` (PK, FK auf auth user)
- `display_name`
- `telegram_chat_id`
- `notify_telegram`, `notify_email`
- `notify_min_score`
- `notify_mode`

## Trennung UserSettings vs AppSettings

- `AppSettings`: globale Admin-Konfiguration
- `UserSettings`: persoenliche Einstellungen pro User
- Telegram-Token global, Telegram-Chat-ID pro User
