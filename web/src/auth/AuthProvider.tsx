import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react"
import { supabase, isSupabaseConfigured } from "@/lib/supabase"
import { FIRM_NAME } from "@/lib/mock"

export interface SignUpArgs {
  email: string
  password: string
  fullName: string
  firmName: string
}

interface AuthContextValue {
  ready: boolean
  authed: boolean
  email: string | null
  firmName: string | null
  signUp: (a: SignUpArgs) => Promise<{ error?: string; needsConfirmation?: boolean }>
  signIn: (login: string, password: string) => Promise<{ error?: string }>
  signOut: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

async function loadFirmName(userId: string, fallback: string | null): Promise<string | null> {
  if (!supabase) return fallback
  try {
    const { data } = await supabase
      .from("profiles")
      .select("firm_name")
      .eq("id", userId)
      .maybeSingle()
    return data?.firm_name ?? fallback
  } catch {
    return fallback
  }
}

function applyUser(
  user: { id: string; email?: string | null; user_metadata?: Record<string, unknown> },
  setEmail: (v: string | null) => void,
  setFirmName: (v: string | null) => void
) {
  const fallback = (user.user_metadata?.firm_name as string | undefined) ?? FIRM_NAME
  setEmail(user.email ?? null)
  setFirmName(fallback)
  void loadFirmName(user.id, fallback).then((name) => {
    if (name) setFirmName(name)
  })
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(false)
  const [email, setEmail] = useState<string | null>(null)
  const [firmName, setFirmName] = useState<string | null>(null)

  useEffect(() => {
    let active = true

    async function boot() {
      if (!isSupabaseConfigured || !supabase) {
        if (active) setReady(true)
        return
      }

      const { data } = await supabase.auth.getSession()
      if (!active) return
      const u = data.session?.user
      if (u) applyUser(u, setEmail, setFirmName)
      setReady(true)
    }

    void boot()

    if (!isSupabaseConfigured || !supabase) {
      return () => {
        active = false
      }
    }

    const { data: sub } = supabase.auth.onAuthStateChange((_e, session) => {
      const u = session?.user
      if (!u) {
        setEmail(null)
        setFirmName(null)
        return
      }
      applyUser(u, setEmail, setFirmName)
    })

    return () => {
      active = false
      sub.subscription.unsubscribe()
    }
  }, [])

  async function signUp(a: SignUpArgs) {
    if (!isSupabaseConfigured || !supabase) {
      return { error: "Sign-in is not configured." }
    }
    const { data, error } = await supabase.auth.signUp({
      email: a.email,
      password: a.password,
      options: { data: { display_name: a.fullName, firm_name: a.firmName } },
    })
    if (error) return { error: error.message }
    if (data.session?.user) {
      applyUser(data.session.user, setEmail, setFirmName)
      return {}
    }
    return { needsConfirmation: true }
  }

  async function signIn(login: string, password: string) {
    if (!isSupabaseConfigured || !supabase) {
      return { error: "Sign-in is not configured." }
    }
    const { data, error } = await supabase.auth.signInWithPassword({
      email: login.trim(),
      password,
    })
    if (error) return { error: error.message }
    if (data.user) applyUser(data.user, setEmail, setFirmName)
    return {}
  }

  async function signOut() {
    if (isSupabaseConfigured && supabase) {
      await supabase.auth.signOut()
    }
    setEmail(null)
    setFirmName(null)
  }

  return (
    <AuthContext.Provider
      value={{
        ready,
        authed: Boolean(email),
        email,
        firmName,
        signUp,
        signIn,
        signOut,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error("useAuth must be used within AuthProvider")
  return ctx
}
