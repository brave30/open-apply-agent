import { useEffect, useState } from 'react'
import { Play, Square } from 'lucide-react'
import { supabase } from './supabase'
import type { CandidateProfile, Resume } from './types'

type Result = { answers: Record<string, string>; resume: Resume | null; success: boolean; steps: number; needs_human: { question: string }[] }
type Job = { id: string; status: string; message: string; preview_image: string | null; result: Result | null }
const active = (job: Job | null) => job && ['queued', 'running'].includes(job.status)

export function AgentRun({ applicationId, profile, requireAuth, onApply }: {
  applicationId: string; profile: CandidateProfile; requireAuth: () => void;
  onApply: (answers: Record<string, string>, resume: Resume | null) => void
}) {
  const [job, setJob] = useState<Job | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [online, setOnline] = useState(false)
  useEffect(() => {
    if (!supabase || !profile.user_id) return
    let alive = true
    async function refresh() {
      const [jobs, health] = await Promise.all([
        supabase!.from('agent_jobs').select('id,status,message,preview_image,result').eq('application_id', applicationId).order('created_at', { ascending: false }).limit(1),
        supabase!.from('agent_worker_health').select('last_seen').limit(1),
      ])
      if (!alive) return
      if (jobs.error || health.error) { setError('Unable to reach the agent service. Please retry.'); return }
      setJob(jobs.data?.[0] as Job || null)
      setOnline(Boolean(health.data?.[0] && Date.now() - Date.parse(health.data[0].last_seen) < 60000))
    }
    void refresh()
    const timer = setInterval(() => void refresh(), 5000)
    return () => { alive = false; clearInterval(timer) }
  }, [applicationId, profile.user_id])
  async function start() {
    if (!profile.user_id) { requireAuth(); return }
    if (!supabase) return
    setBusy(true); setError('')
    try {
      const { data: saved, error: profileError } = await supabase.from('candidate_profiles').select('resume').eq('user_id', profile.user_id).single()
      if (profileError || !saved?.resume) throw new Error('Save your profile and upload a resume in My profile first.')
      const { data: signed, error: signError } = await supabase.storage.from('resumes').createSignedUrl(saved.resume.path, 3600)
      if (signError) throw signError
      const { data: id, error: startError } = await supabase.rpc('start_agent_job', { application: applicationId, signed_resume_url: signed.signedUrl })
      if (startError) throw startError
      setJob({ id, status: 'queued', message: 'Waiting for the server…', preview_image: null, result: null })
    } catch (e) { setError(e instanceof Error ? e.message : String((e as { message?: string }).message || 'Unable to start the agent.')) }
    finally { setBusy(false) }
  }
  async function cancel() {
    if (!supabase || !job) return
    setBusy(true)
    const { error } = await supabase.rpc('cancel_agent_job', { job_id: job.id })
    if (error) setError(error.message)
    else setJob({ ...job, status: 'cancelled', message: 'Cancelled.' })
    setBusy(false)
  }
  return <section className="panel agent-panel" aria-label="Computer-use agent">
    <div className="agent-heading"><div><h2>Let the agent take a first pass.</h2><p className="muted">OpenWebRL uses a browser to fill this simulation with your saved facts. You review the answers before submitting.</p></div>
      <button className="button primary" disabled={busy || Boolean(active(job))} onClick={() => void start()}><Play size={15}/>{busy ? 'Starting…' : 'Start Agent'}</button></div>
    {profile.user_id && <small className="muted">{online ? 'Agent server online · one run at a time' : 'Agent server offline · retry when it is available'}</small>}
    {error && <p className="notice" role="alert">{error}</p>}
    {job && <div className="agent-status"><p role="status"><strong>{job.status === 'completed' ? 'Ready for review' : job.status.charAt(0).toUpperCase() + job.status.slice(1)}</strong> · {job.message}</p>
      {active(job) && <button className="button secondary small" disabled={busy} onClick={() => void cancel()}><Square size={13}/> Cancel run</button>}
      {job.preview_image?.startsWith('data:image/jpeg;base64,') && <img className="agent-preview" src={job.preview_image} alt="Latest screenshot from the agent’s application browser"/>}
      {job.status === 'completed' && job.result && <><p>{Object.keys(job.result.answers).length} verified answers · {job.result.steps} actions · {job.result.success ? 'Fill verified' : 'Partial result — review required'}</p>
        {Boolean(job.result.needs_human.length) && <p className="muted">Needs your input: {job.result.needs_human.map(q => q.question).join(', ')}.</p>}
        <button className="button secondary" onClick={() => onApply(job.result!.answers, job.result!.resume)}>Use verified answers in my draft</button>
        <p className="muted">This replaces the current form answers. Nothing has been submitted.</p></>}
    </div>}
  </section>
}
