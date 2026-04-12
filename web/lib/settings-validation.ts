/** Grenzen wie im Backend (`UserProfileUpdate` / SQLModel). */
export const DISPLAY_NAME_MAX_LENGTH = 50

/** Mindestens ein Unicode-Buchstabe (wie Backend `unicodedata` Kategorie L*). */
const DISPLAY_NAME_HAS_LETTER = /\p{L}/u

export function displayNameHasAtLeastOneLetter(trimmed: string): boolean {
  return DISPLAY_NAME_HAS_LETTER.test(trimmed)
}

export type SettingsSaveFieldErrors = {
  displayName?: string
  telegramChatId?: string
}

export type SettingsSaveInput = {
  displayName: string
  notifyTelegram: boolean
  telegramConfigured: boolean
  telegramChatId: string
}

export function getSettingsSaveValidationErrors(
  input: SettingsSaveInput,
): SettingsSaveFieldErrors {
  const errors: SettingsSaveFieldErrors = {}
  const name = input.displayName.trim()
  if (name.length > DISPLAY_NAME_MAX_LENGTH) {
    errors.displayName = `Der Name darf höchstens ${DISPLAY_NAME_MAX_LENGTH} Zeichen haben.`
  } else if (!name) {
    errors.displayName =
      "Bitte gib einen Namen ein — mindestens ein Buchstabe ist erforderlich (Leerzeichen am Rand zählen nicht)."
  } else if (!displayNameHasAtLeastOneLetter(name)) {
    errors.displayName =
      "Der Name muss mindestens einen Buchstaben enthalten (Ziffern oder Sonderzeichen allein reichen nicht)."
  }
  if (input.notifyTelegram && input.telegramConfigured) {
    const chat = input.telegramChatId.trim()
    if (!chat) {
      errors.telegramChatId =
        "Wenn Telegram-Benachrichtigungen an sind, wird eine numerische Chat-ID benötigt."
    } else if (!/^-?\d+$/.test(chat)) {
      errors.telegramChatId =
        "Die Chat-ID besteht aus Ziffern. Bei Supergruppen steht oft ein Minus am Anfang (z. B. -100…)."
    }
  }
  return errors
}

export function settingsSaveHasErrors(errors: SettingsSaveFieldErrors): boolean {
  return Object.values(errors).some(Boolean)
}

/**
 * Typische englische FastAPI-/Pydantic-Meldungen für die Profil-/Settings-Payload
 * in verständliche deutsche Hinweise umsetzen.
 */
export function humanizeSettingsSaveApiError(message: string): string {
  const t = message.trim()
  const lower = t.toLowerCase()

  if (lower.includes("mindestens einen buchstaben")) {
    return "Der Name muss mindestens einen Buchstaben enthalten (Leerzeichen am Rand zählen nicht)."
  }
  if (
    lower.includes("at least 1 character") ||
    lower.includes("ensure this value has at least 1")
  ) {
    return "Der Name darf nicht leer sein. Bitte gib unter „Name“ mindestens ein Zeichen ein (Leerzeichen am Rand zählen nicht)."
  }
  if (
    (lower.includes("at most") && lower.includes("character")) ||
    lower.includes("ensure this value has at most") ||
    lower.includes("string too long")
  ) {
    return `Der Name ist zu lang — maximal ${DISPLAY_NAME_MAX_LENGTH} Zeichen erlaubt.`
  }
  if (lower.includes("field required") || lower === "field required") {
    return "Ein benötigtes Feld fehlt. Bitte prüfe den Namen und speichere erneut."
  }

  return t
}
