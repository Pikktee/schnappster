export interface PasswordCheck {
  minLength: boolean
  hasUppercase: boolean
  hasLowercase: boolean
  hasSpecialChar: boolean
}

export type PasswordStrength = "none" | "weak" | "medium" | "strong"

export function checkPassword(password: string): PasswordCheck {
  return {
    minLength: password.length >= 8,
    hasUppercase: /[A-Z]/.test(password),
    hasLowercase: /[a-z]/.test(password),
    hasSpecialChar: /[^A-Za-z0-9]/.test(password),
  }
}

export function getPasswordStrength(password: string): PasswordStrength {
  if (!password) return "none"
  const checks = checkPassword(password)
  const passed = Object.values(checks).filter(Boolean).length
  if (passed <= 2) return "weak"
  if (passed === 3) return "medium"
  return "strong"
}

export function isPasswordValid(password: string): boolean {
  const checks = checkPassword(password)
  return Object.values(checks).every(Boolean)
}
