import { useState, type FormEvent } from 'react'
import { ArrowRight, LockKeyhole, Mail } from 'lucide-react'
import { supabase } from './supabase'

export function Auth({ close }: { close: () => void }) {
  const [mode, setMode] = useState<'signin' | 'signup' | 'reset'>('signin')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  async function submit(e: FormEvent) {
    e.preventDefault()
    if (!supabase) { setMessage('Account creation will be available when Supabase setup is complete.'); return }
    setBusy(true); setMessage('')
    try {
      const { data, error } = mode === 'reset'
        ? await supabase.auth.resetPasswordForEmail(email, { redirectTo: location.origin })
        : mode === 'signup'
          ? await supabase.auth.signUp({ email, password, options: { emailRedirectTo: location.origin } })
          : await supabase.auth.signInWithPassword({ email, password })
      if (error) throw error
      if (data && 'session' in data && data.session) close()
      else setMessage(mode === 'reset' ? 'Check your email for a password reset link.' : 'Check your email to confirm your account, then sign in.')
    } catch (error) { setMessage(error instanceof Error ? error.message : 'Unable to sign in. Try again.') }
    finally { setBusy(false) }
  }
  return <div className="modal-backdrop"><section className="modal" role="dialog" aria-modal="true" aria-labelledby="auth-title"><button className="modal-close" aria-label="Close sign in" onClick={close}>×</button><span className="eyebrow">YOUR NEXT CHAPTER</span><h2 id="auth-title">{mode === 'signup' ? 'Make yourself at home.' : mode === 'reset' ? 'Reset your password.' : 'Welcome back.'}</h2><p className="muted">One profile. Your own application workspace.</p><form onSubmit={submit}><label><span><Mail size={14}/> Email address</span><input autoFocus type="email" required value={email} onChange={e => setEmail(e.target.value)} autoComplete="email"/></label>{mode !== 'reset' && <label><span><LockKeyhole size={14}/> Password</span><input type="password" required minLength={8} value={password} onChange={e => setPassword(e.target.value)} autoComplete={mode === 'signup' ? 'new-password' : 'current-password'}/></label>}<button className="button primary full" disabled={busy}>{busy ? 'Please wait…' : mode === 'signup' ? 'Create account' : mode === 'reset' ? 'Send reset link' : 'Sign in'}<ArrowRight size={16}/></button></form>{message && <p role="status" className="notice">{message}</p>}<div className="auth-links"><button onClick={() => { setMode(mode === 'signup' ? 'signin' : 'signup'); setMessage('') }}>{mode === 'signup' ? 'Already have an account? Sign in' : 'New here? Create an account'}</button><button onClick={() => { setMode('reset'); setMessage('') }}>Forgot password?</button></div></section></div>
}
