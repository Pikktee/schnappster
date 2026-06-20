"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { toast } from "sonner"
import { KeyRound, Lock, ShieldCheck, Trash2, UserPlus } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Skeleton } from "@/components/ui/skeleton"
import { EmptyState } from "@/components/empty-state"
import { ContentReveal } from "@/components/content-reveal"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { PasswordStrengthIndicator } from "@/components/password-strength-indicator"
import { isPasswordValid } from "@/lib/password-validation"
import {
  createUser,
  deleteUser,
  fetchUsers,
  resetUserPassword,
  updateUser,
} from "@/lib/api"
import type { AdminUser } from "@/lib/types"
import { useAuth } from "@/components/auth-provider"
import { timeAgo } from "@/lib/format"

function errorMessage(e: unknown, fallback: string): string {
  return e instanceof Error ? e.message : fallback
}

export default function UsersPage() {
  const router = useRouter()
  const { user, loading: authLoading } = useAuth()

  const [users, setUsers] = useState<AdminUser[]>([])
  const [loading, setLoading] = useState(true)
  const [busyId, setBusyId] = useState<string | null>(null)

  const [createOpen, setCreateOpen] = useState(false)
  const [newEmail, setNewEmail] = useState("")
  const [newPassword, setNewPassword] = useState("")
  const [newRole, setNewRole] = useState("user")
  const [newActive, setNewActive] = useState(true)
  const [creating, setCreating] = useState(false)

  const [resetTarget, setResetTarget] = useState<AdminUser | null>(null)
  const [resetPassword, setResetPasswordValue] = useState("")
  const [resetting, setResetting] = useState(false)

  const [deleteTarget, setDeleteTarget] = useState<AdminUser | null>(null)
  const [deleting, setDeleting] = useState(false)

  // Nicht-Admins haben hier nichts zu suchen.
  useEffect(() => {
    if (!authLoading && user && user.role !== "admin") {
      router.replace("/dashboard")
    }
  }, [authLoading, user, router])

  const isAdmin = user?.role === "admin"

  useEffect(() => {
    if (!isAdmin) return
    let cancelled = false
    setLoading(true)
    fetchUsers()
      .then((data) => {
        if (!cancelled) setUsers(data)
      })
      .catch((e) => {
        if (!cancelled) toast.error(errorMessage(e, "Benutzer konnten nicht geladen werden."))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [isAdmin])

  async function reload() {
    try {
      setUsers(await fetchUsers())
    } catch (e) {
      toast.error(errorMessage(e, "Benutzer konnten nicht geladen werden."))
    }
  }

  async function handleToggleActive(target: AdminUser) {
    setBusyId(target.id)
    try {
      await updateUser(target.id, { is_active: !target.is_active })
      toast.success(target.is_active ? "Konto gesperrt." : "Konto freigeschaltet.")
      await reload()
    } catch (e) {
      toast.error(errorMessage(e, "Aktion fehlgeschlagen."))
    } finally {
      setBusyId(null)
    }
  }

  async function handleRoleChange(target: AdminUser, role: string) {
    if (role === target.role) return
    setBusyId(target.id)
    try {
      await updateUser(target.id, { role })
      toast.success("Rolle aktualisiert.")
      await reload()
    } catch (e) {
      toast.error(errorMessage(e, "Rolle konnte nicht geändert werden."))
    } finally {
      setBusyId(null)
    }
  }

  async function handleCreate() {
    if (!isPasswordValid(newPassword)) {
      toast.error("Passwort erfüllt nicht alle Anforderungen.")
      return
    }
    setCreating(true)
    try {
      await createUser({
        email: newEmail.trim(),
        password: newPassword,
        role: newRole,
        is_active: newActive,
      })
      toast.success("Benutzer angelegt.")
      setCreateOpen(false)
      setNewEmail("")
      setNewPassword("")
      setNewRole("user")
      setNewActive(true)
      await reload()
    } catch (e) {
      toast.error(errorMessage(e, "Benutzer konnte nicht angelegt werden."))
    } finally {
      setCreating(false)
    }
  }

  async function handleResetPassword() {
    if (!resetTarget) return
    if (!isPasswordValid(resetPassword)) {
      toast.error("Passwort erfüllt nicht alle Anforderungen.")
      return
    }
    setResetting(true)
    try {
      await resetUserPassword(resetTarget.id, resetPassword)
      toast.success("Passwort zurückgesetzt.")
      setResetTarget(null)
      setResetPasswordValue("")
    } catch (e) {
      toast.error(errorMessage(e, "Passwort konnte nicht zurückgesetzt werden."))
    } finally {
      setResetting(false)
    }
  }

  async function handleDelete() {
    if (!deleteTarget) return
    setDeleting(true)
    try {
      await deleteUser(deleteTarget.id)
      toast.success("Benutzer gelöscht.")
      setDeleteTarget(null)
      await reload()
    } catch (e) {
      toast.error(errorMessage(e, "Benutzer konnte nicht gelöscht werden."))
    } finally {
      setDeleting(false)
    }
  }

  if (authLoading || !isAdmin) {
    return <Skeleton className="h-64 w-full max-w-4xl" />
  }

  return (
    <ContentReveal className="flex flex-col gap-6 min-w-0">
      <div className="flex justify-end">
        <Button onClick={() => setCreateOpen(true)} className="gap-2">
          <UserPlus className="size-4" />
          Benutzer anlegen
        </Button>
      </div>

      {loading ? (
        <Skeleton className="h-64 w-full" />
      ) : users.length === 0 ? (
        <EmptyState message="Keine Benutzer vorhanden." />
      ) : (
        <div className="overflow-x-auto rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>E-Mail</TableHead>
                <TableHead>Name</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Rolle</TableHead>
                <TableHead>Angelegt</TableHead>
                <TableHead className="text-right">Aktionen</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {users.map((u) => {
                const isSelf = u.id === user?.id
                const busy = busyId === u.id
                return (
                  <TableRow key={u.id}>
                    <TableCell className="font-medium">{u.email}</TableCell>
                    <TableCell className="text-muted-foreground">{u.display_name || "—"}</TableCell>
                    <TableCell>
                      {u.is_active ? (
                        <Badge variant="secondary">Aktiv</Badge>
                      ) : (
                        <Badge variant="outline" className="text-amber-700 dark:text-amber-300">
                          Gesperrt
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell>
                      <Select
                        value={u.role}
                        onValueChange={(v) => void handleRoleChange(u, v)}
                        disabled={busy || isSelf}
                      >
                        <SelectTrigger className="h-8 w-32">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="user">Mitglied</SelectItem>
                          <SelectItem value="admin">Administrator</SelectItem>
                        </SelectContent>
                      </Select>
                    </TableCell>
                    <TableCell className="text-muted-foreground tabular-nums">
                      {timeAgo(u.created_at)}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center justify-end gap-1">
                        <Button
                          variant="outline"
                          size="sm"
                          className="gap-1.5"
                          disabled={busy || isSelf}
                          onClick={() => void handleToggleActive(u)}
                        >
                          {u.is_active ? (
                            <>
                              <Lock className="size-3.5" />
                              Sperren
                            </>
                          ) : (
                            <>
                              <ShieldCheck className="size-3.5" />
                              Freischalten
                            </>
                          )}
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          title="Passwort zurücksetzen"
                          onClick={() => {
                            setResetTarget(u)
                            setResetPasswordValue("")
                          }}
                        >
                          <KeyRound className="size-4" />
                          <span className="sr-only">Passwort zurücksetzen</span>
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          title="Benutzer löschen"
                          className="text-destructive hover:text-destructive"
                          disabled={isSelf}
                          onClick={() => setDeleteTarget(u)}
                        >
                          <Trash2 className="size-4" />
                          <span className="sr-only">Benutzer löschen</span>
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </div>
      )}

      {/* Benutzer anlegen */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Benutzer anlegen</DialogTitle>
            <DialogDescription>
              Lege ein neues Konto an. Du kannst es direkt aktiv schalten.
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-4">
            <div className="flex flex-col gap-2">
              <Label htmlFor="new-email">E-Mail</Label>
              <Input
                id="new-email"
                type="email"
                value={newEmail}
                autoComplete="off"
                onChange={(e) => setNewEmail(e.target.value)}
              />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="new-password">Passwort</Label>
              <Input
                id="new-password"
                type="password"
                value={newPassword}
                autoComplete="new-password"
                onChange={(e) => setNewPassword(e.target.value)}
              />
              <PasswordStrengthIndicator password={newPassword} />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="new-role">Rolle</Label>
              <Select value={newRole} onValueChange={setNewRole}>
                <SelectTrigger id="new-role">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="user">Mitglied</SelectItem>
                  <SelectItem value="admin">Administrator</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="new-active">Status</Label>
              <Select
                value={newActive ? "active" : "inactive"}
                onValueChange={(v) => setNewActive(v === "active")}
              >
                <SelectTrigger id="new-active">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="active">Aktiv</SelectItem>
                  <SelectItem value="inactive">Gesperrt</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateOpen(false)}>
              Abbrechen
            </Button>
            <Button
              onClick={() => void handleCreate()}
              disabled={creating || !newEmail.trim() || !isPasswordValid(newPassword)}
            >
              {creating ? "Anlegen..." : "Anlegen"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Passwort zurücksetzen */}
      <Dialog
        open={Boolean(resetTarget)}
        onOpenChange={(open) => {
          if (!open) {
            setResetTarget(null)
            setResetPasswordValue("")
          }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Passwort zurücksetzen</DialogTitle>
            <DialogDescription>
              Neues Passwort für {resetTarget?.email} festlegen.
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-2">
            <Label htmlFor="reset-password">Neues Passwort</Label>
            <Input
              id="reset-password"
              type="password"
              value={resetPassword}
              autoComplete="new-password"
              onChange={(e) => setResetPasswordValue(e.target.value)}
            />
            <PasswordStrengthIndicator password={resetPassword} />
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setResetTarget(null)
                setResetPasswordValue("")
              }}
            >
              Abbrechen
            </Button>
            <Button
              onClick={() => void handleResetPassword()}
              disabled={resetting || !isPasswordValid(resetPassword)}
            >
              {resetting ? "Speichern..." : "Passwort speichern"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Benutzer löschen */}
      <AlertDialog
        open={Boolean(deleteTarget)}
        onOpenChange={(open) => {
          if (!open) setDeleteTarget(null)
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Benutzer wirklich löschen?</AlertDialogTitle>
            <AlertDialogDescription>
              {deleteTarget?.email} wird dauerhaft gelöscht. Diese Aktion kann nicht rückgängig
              gemacht werden.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Abbrechen</AlertDialogCancel>
            <AlertDialogAction onClick={() => void handleDelete()}>
              {deleting ? "Lösche..." : "Ja, löschen"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </ContentReveal>
  )
}
