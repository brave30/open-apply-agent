import { useState, type FormEvent } from 'react'
import { ArrowLeft, ArrowRight, Check, FileCheck, Save, Sparkles } from 'lucide-react'
import { fieldsFor } from './catalog'
import { matchProfile } from './profile-matching'
import { saveDraft, submitDraft } from './data'
import type { Application, CandidateProfile, Draft } from './types'
import { AgentRun } from './AgentRun'

export function ApplicationForm({ application: app, profile, existing, onSaved, back, requireAuth }: { application: Application; profile: CandidateProfile; existing?: Draft; onSaved: (d: Draft) => void; back: () => void; requireAuth: () => void }) {
  const fields = fieldsFor(app)
  const sections = [...new Set(fields.map(f => f.section)), 'Resume']
  const multipage = app.platform === 'Workday' || (app.platform === 'Other' && app.variant === 5)
  const [step, setStep] = useState(0)
  const [draft, setDraft] = useState<Draft>(existing || { user_id: profile.user_id, application_id: app.id, answers: {}, resume: null, status: 'draft' })
  const [review, setReview] = useState(false)
  const [confirmed, setConfirmed] = useState(false)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  async function save() {
    if (!profile.user_id) { requireAuth(); return }
    setBusy(true); setMessage('')
    try { const saved = await saveDraft({ ...draft, user_id: profile.user_id }); setDraft(saved); onSaved(saved); setMessage('Draft saved.') }
    catch (e) { setMessage(e instanceof Error ? e.message : 'Unable to save.') }
    finally { setBusy(false) }
  }
  async function submit() {
    if (!profile.user_id) { requireAuth(); return }
    if (!confirmed) return
    setBusy(true); setMessage('')
    try {
      const saved = await saveDraft({ ...draft, user_id: profile.user_id })
      await submitDraft(saved.id!, saved.answers, saved.resume)
      const done = { ...saved, status: 'submitted' as const }; setDraft(done); onSaved(done); setReview(false)
    } catch (e) { setMessage(e instanceof Error ? e.message : 'Submission failed.') }
    finally { setBusy(false) }
  }
  function next(e: FormEvent) {
    e.preventDefault()
    if (multipage && step < sections.length - 1) { setStep(step + 1); return }
    const missing = fields.filter(f => f.required && !draft.answers[f.id]?.trim())
    if (missing.length) { setMessage(`Please complete: ${missing.map(f => f.label).join(', ')}.`); setStep(0); return }
    if (!draft.resume) { setMessage('Add a resume to your profile, then attach it here.'); return }
    setReview(true); setConfirmed(false); setMessage('')
  }
  function fill() {
    const matches = matchProfile(fields, profile)
    setDraft({ ...draft, answers: { ...matches, ...Object.fromEntries(Object.entries(draft.answers).filter(([, value]) => value.trim())) }, resume: draft.resume || profile.resume })
    setMessage(`${Object.keys(matches).length} stored answers matched. Review each answer; unknown questions remain empty.`)
  }
  if (draft.status === 'submitted') return <div className="success-state"><span className="success-icon"><Check size={32}/></span><span className="eyebrow">PRACTICE MAKES PROGRESS</span><h1>Application complete.</h1><p>Your simulated application to {app.company} was saved.<br/>No application was sent to a real employer.</p><button className="button primary" onClick={back}>Back to applications <ArrowRight size={16}/></button></div>
  return <><button className="text-button" onClick={back}><ArrowLeft size={15}/> Back to applications</button><div className={`application-header platform-${app.platform.toLowerCase()}`}><span className="eyebrow">{app.company.toUpperCase()} · {app.platform.toUpperCase()} STYLE</span><h1>{app.title}</h1><p>{app.location} <span>·</span> {app.department}</p><span className="badge">Simulated application</span></div><AgentRun applicationId={app.id} profile={profile} requireAuth={requireAuth} onApply={(answers, resume) => { setDraft({ ...draft, answers, resume }); setStep(0); setMessage("Agent answers loaded. Review them and save your draft.") }}/><div className="application-layout"><div><div className="form-toolbar"><span><FileCheck size={17}/> Your application</span><button className="button secondary small" onClick={fill}><Sparkles size={14}/> Fill from my profile</button></div>{multipage && <div className="steps" aria-label="Application progress">{sections.map((s, i) => <span key={s} className={i === step ? 'active' : ''}>{i + 1}. {s}</span>)}</div>}
  <form onSubmit={next}>{sections.filter(s => !multipage || s === sections[step]).map(section => <section className="panel" key={section}><h2>{section}</h2>{section === 'Resume' ? <div className="resume-attach"><p>{draft.resume ? `Attached: ${draft.resume.name}` : 'No resume attached.'}</p><button type="button" className="button secondary small" disabled={!profile.resume} onClick={() => setDraft({ ...draft, resume: profile.resume })}>Attach profile resume</button><p className="muted">Upload or change your resume in My profile.</p></div> : <div className={app.platform === 'Lever' ? 'form-grid single' : 'form-grid'}>{fields.filter(f => f.section === section).map(f => <label key={f.id} className={f.type === 'textarea' ? 'wide' : ''} htmlFor={f.id}>{f.label}{f.required && ' *'}{f.type === 'textarea' ? <textarea id={f.id} name={f.id} value={draft.answers[f.id] || ''} required={f.required} onChange={e => setDraft({ ...draft, answers: { ...draft.answers, [f.id]: e.target.value } })}/> : f.type === 'select' ? <select id={f.id} name={f.id} value={draft.answers[f.id] || ''} onChange={e => setDraft({ ...draft, answers: { ...draft.answers, [f.id]: e.target.value } })}>{f.options?.map(o => <option key={o} value={o}>{o || 'Select an answer'}</option>)}</select> : <input id={f.id} name={f.id} type={f.type || 'text'} value={draft.answers[f.id] || ''} required={f.required} onChange={e => setDraft({ ...draft, answers: { ...draft.answers, [f.id]: e.target.value } })}/>}</label>)}</div>}</section>) }
  {message && <p className="notice" role="status">{message}</p>}<div className="application-actions"><button className="button secondary" type="button" disabled={busy} onClick={() => void save()}><Save size={15}/> Save draft</button><div>{multipage && step > 0 && <button className="button secondary" type="button" onClick={() => setStep(step - 1)}>Previous</button>}<button className="button primary" disabled={busy}>{multipage && step < sections.length - 1 ? 'Continue' : 'Review application'}<ArrowRight size={16}/></button></div></div></form></div><aside className="application-aside"><span className="eyebrow">ABOUT THIS ROLE</span><h3>Build something that matters.</h3><p>{app.description}</p><hr/><h4>A note on your data</h4><p>Your draft stays private to your account. This is a testing environment; no information is shared with real employers.</p></aside></div>
  {review && <div className="modal-backdrop"><section className="modal review-modal" role="dialog" aria-modal="true" aria-labelledby="review-title"><button className="modal-close" aria-label="Close review" onClick={() => setReview(false)}>×</button><span className="eyebrow">ONE LAST LOOK</span><h2 id="review-title">Review your application.</h2><p className="muted">{app.company} · {app.title}</p><dl className="review-list">{fields.map(f => <div key={f.id}><dt>{f.label}</dt><dd>{draft.answers[f.id] || 'Not answered'}</dd></div>)}<div><dt>Resume</dt><dd>{draft.resume?.name || 'Not attached'}</dd></div></dl><label className="checkbox-label"><input type="checkbox" checked={confirmed} onChange={e => setConfirmed(e.target.checked)}/> I reviewed these answers and approve saving this simulated submission.</label>{message && <p role="status" className="notice">{message}</p>}<button className="button primary full" disabled={!confirmed || busy} onClick={() => void submit()}>{busy ? 'Saving…' : 'Submit simulated application'}<ArrowRight size={16}/></button></section></div>}</>
}
