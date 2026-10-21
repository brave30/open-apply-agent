import { useState, type FormEvent } from 'react'
import { Check, Plus, Save, Trash2, Upload } from 'lucide-react'
import { saveProfile, uploadResume } from './data'
import type { CandidateProfile } from './types'

export function ProfileEditor({ profile, onSaved, requireAuth }: { profile: CandidateProfile; onSaved: (p: CandidateProfile) => void; requireAuth: () => void }) {
  const [p, setP] = useState(() => structuredClone(profile))
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [skills, setSkills] = useState(p.skills.join(', '))
  const updatePersonal = (key: keyof CandidateProfile['personal'], value: string) => setP({ ...p, personal: { ...p.personal, [key]: value } })
  async function save(e: FormEvent) {
    e.preventDefault()
    if (!p.user_id) { requireAuth(); return }
    setBusy(true); setMessage('')
    const next = { ...p, skills: skills.split(',').map(s => s.trim()).filter(Boolean) }
    try { await saveProfile(next); setP(next); onSaved(next); setMessage('Profile saved to your account.') }
    catch (e) { setMessage(e instanceof Error ? e.message : 'Could not save profile.') }
    finally { setBusy(false) }
  }
  async function upload(file?: File) {
    if (!file) return
    if (!p.user_id) { requireAuth(); return }
    setBusy(true); setMessage('')
    try {
      const resume = await uploadResume(p.user_id, file)
      const next = { ...p, resume, skills: skills.split(',').map(s => s.trim()).filter(Boolean) }
      await saveProfile(next); setP(next); onSaved(next); setMessage('Resume uploaded and profile saved.')
    } catch (e) { setMessage(e instanceof Error ? e.message : 'Resume upload failed.') }
    finally { setBusy(false) }
  }
  return <><div className="page-heading"><div><span className="eyebrow">THE PERSON BEHIND THE APPLICATION</span><h1>My profile<span className="heading-dot">.</span></h1><p className="muted">Your story, ready for the next opportunity.</p></div><span className="badge green"><Check size={13}/> Private to your account</span></div>
  <form className="profile-form" onSubmit={save}>
    <section className="panel"><div className="section-heading"><div><h2>Personal information</h2><p>How employers can get to know you.</p></div><span className="section-number">01</span></div><div className="form-grid">{([
      ['full_name', 'Full name', 'text', true], ['email', 'Email address', 'email', true], ['phone', 'Phone number', 'tel', false], ['city', 'City', 'text', false], ['linkedin', 'LinkedIn', 'url', false],
    ] as const).map(([key, label, type, required]) => <label key={key}>{label}{required && ' *'}<input name={key} type={type} required={required} value={p.personal[key]} onChange={e => updatePersonal(key, e.target.value)} placeholder={key === 'linkedin' ? 'https://linkedin.com/in/you' : undefined}/></label>)}</div></section>
    <section className="panel"><div className="section-heading"><div><h2>Education</h2><p>Add your education records. Multiple records require a selection when applying.</p></div><button className="button secondary small" type="button" onClick={() => setP({ ...p, education: [...p.education, { school: '', degree: '', field: '', graduation_year: new Date().getFullYear() }] })}><Plus size={14}/> Add education</button></div>{p.education.length === 0 && <p className="empty-inline">No education added yet.</p>}{p.education.map((entry, i) => <div className="repeat-record" key={i}><div className="form-grid">{(['school', 'degree', 'field', 'graduation_year'] as const).map(key => <label key={key}>{key.replaceAll('_', ' ')}<input required type={key === 'graduation_year' ? 'number' : 'text'} min={key === 'graduation_year' ? 1900 : undefined} max={key === 'graduation_year' ? 2100 : undefined} value={entry[key]} onChange={e => setP({ ...p, education: p.education.map((v, j) => j === i ? { ...v, [key]: key === 'graduation_year' ? Number(e.target.value) : e.target.value } : v) })}/></label>)}</div><button type="button" className="text-button danger" onClick={() => setP({ ...p, education: p.education.filter((_, j) => i !== j) })}><Trash2 size={13}/> Remove education</button></div>)}</section>
    <section className="panel"><div className="section-heading"><div><h2>Work experience</h2><p>Keep your professional history in one place.</p></div><button className="button secondary small" type="button" onClick={() => setP({ ...p, work_experience: [...p.work_experience, { employer: '', title: '', start_date: '', end_date: null, description: '' }] })}><Plus size={14}/> Add experience</button></div>{p.work_experience.length === 0 && <p className="empty-inline">No work experience added yet.</p>}{p.work_experience.map((entry, i) => <div className="repeat-record" key={i}><div className="form-grid">{(['employer', 'title', 'start_date', 'end_date', 'description'] as const).map(key => <label key={key}>{key.replaceAll('_', ' ')}{key === 'description' ? <textarea value={entry[key]} onChange={e => setP({ ...p, work_experience: p.work_experience.map((v, j) => j === i ? { ...v, [key]: e.target.value } : v) })}/> : <input type={key.endsWith('date') ? 'month' : 'text'} required={key !== 'end_date'} value={entry[key] || ''} onChange={e => setP({ ...p, work_experience: p.work_experience.map((v, j) => j === i ? { ...v, [key]: e.target.value || null } : v) })}/>}</label>)}</div><button type="button" className="text-button danger" onClick={() => setP({ ...p, work_experience: p.work_experience.filter((_, j) => i !== j) })}><Trash2 size={13}/> Remove experience</button></div>)}</section>
    <section className="panel"><div className="section-heading"><div><h2>Skills & resume</h2><p>Documents are stored privately in your account.</p></div><span className="section-number">04</span></div><label>Skills, separated by commas<input value={skills} onChange={e => setSkills(e.target.value)} placeholder="Python, SQL, React"/></label><label className="upload-area"><Upload size={22}/><strong>{p.resume ? p.resume.name : 'Upload your resume'}</strong><span>PDF, DOCX or TXT · Up to 5 MB</span><input aria-label="Upload resume" type="file" accept=".pdf,.docx,.txt" disabled={busy} onChange={e => { void upload(e.target.files?.[0]); e.target.value = '' }}/></label></section>
    <section className="panel"><div className="section-heading"><div><h2>Verified answers</h2><p>Only confirmed answers are used to fill matching application questions.</p></div><button className="button secondary small" type="button" onClick={() => setP({ ...p, verified_answers: [...p.verified_answers, { question: '', value: '', verified: false, verified_at: null, source: 'Candidate' }] })}><Plus size={14}/> Add answer</button></div>{p.verified_answers.length === 0 && <p className="empty-inline">Add common answers such as work authorization or availability.</p>}{p.verified_answers.map((a, i) => <div className="repeat-record" key={i}><div className="form-grid"><label>Exact question<input required value={a.question} onChange={e => setP({ ...p, verified_answers: p.verified_answers.map((v, j) => i === j ? { ...v, question: e.target.value } : v) })}/></label><label>Your answer<input required value={a.value} onChange={e => setP({ ...p, verified_answers: p.verified_answers.map((v, j) => i === j ? { ...v, value: e.target.value } : v) })}/></label></div><label className="checkbox-label"><input type="checkbox" checked={a.verified} onChange={e => setP({ ...p, verified_answers: p.verified_answers.map((v, j) => i === j ? { ...v, verified: e.target.checked, verified_at: e.target.checked ? new Date().toISOString().slice(0,10) : null } : v) })}/> I confirm this answer is accurate.</label><button type="button" className="text-button danger" onClick={() => setP({ ...p, verified_answers: p.verified_answers.filter((_, j) => i !== j) })}>Remove answer</button></div>)}</section>
    <div className="save-bar"><span role="status">{message || 'You control the details you share.'}</span><button className="button primary" disabled={busy}><Save size={16}/>{busy ? 'Saving…' : 'Save profile'}</button></div>
  </form></>
}
