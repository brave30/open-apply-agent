import { useEffect, useState } from 'react'
import type { User } from '@supabase/supabase-js'
import { ArrowDownUp, ArrowRight, BriefcaseBusiness, Check, FileText, Search, ShieldCheck, Sparkles, UserRound } from 'lucide-react'
import { DashboardNavigationProvider, useDashboardNavigation } from './components/navigation'
import { Workspace } from './components/Workspace'
import { applications } from './catalog'
import { configured, supabase } from './supabase'
import { getDrafts, getProfile } from './data'
import { emptyProfile, type CandidateProfile, type Draft, type Platform } from './types'
import { Auth } from './Auth'
import { ProfileEditor } from './ProfileEditor'
import { ApplicationForm } from './ApplicationForm'

function Content() {
  const { pathname, navigate } = useDashboardNavigation()
  const [user, setUser] = useState<User | null>(null)
  const [profile, setProfile] = useState<CandidateProfile>(emptyProfile())
  const [drafts, setDrafts] = useState<Draft[]>([])
  const [auth, setAuth] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [recovery, setRecovery] = useState(false)
  const [newPassword, setNewPassword] = useState('')
  useEffect(() => {
    if (!supabase) { setLoading(false); return }
    let alive = true
    void supabase.auth.getSession().then(({ data, error }) => { if (!alive) return; if (error) setError(error.message); setUser(data.session?.user || null); setLoading(false) })
    const { data } = supabase.auth.onAuthStateChange((event, session) => { if (!alive) return; setUser(session?.user || null); if (event === 'PASSWORD_RECOVERY') setRecovery(true); if (session) setAuth(false) })
    return () => { alive = false; data.subscription.unsubscribe() }
  }, [])
  useEffect(() => {
    if (!user) { setProfile(emptyProfile()); setDrafts([]); return }
    let alive = true
    setProfile(emptyProfile(user.id, user.email || '')); setDrafts([])
    setLoading(true); setError('')
    void Promise.all([getProfile(user.id, user.email || ''), getDrafts(user.id)]).then(([p, d]) => { if (alive) { setProfile(p); setDrafts(d) } }).catch(e => { if (alive) setError(e.message) }).finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [user?.id])
  const onSaved = (draft: Draft) => setDrafts(d => [draft, ...d.filter(v => v.application_id !== draft.application_id)])
  const app = pathname.startsWith('/apply/') ? applications.find(a => a.id === pathname.slice(7)) : undefined
  return <Workspace email={user?.email} signOut={() => { void supabase?.auth.signOut().then(({ error }) => { if (error) setError(error.message) }); navigate('/') }}>
    {!configured && <div className="setup-banner"><ShieldCheck size={16}/> Preview mode · Sign-in and cloud saving will be enabled after the Supabase project is connected.</div>}
    {error && <div className="notice" role="alert">{error}<button className="text-button" onClick={() => location.reload()}>Retry</button></div>}
    {loading ? <div className="loading" role="status">Opening your workspace…</div> : app ? <ApplicationForm key={`${app.id}-${user?.id || 'guest'}`} application={app} profile={profile} existing={drafts.find(d => d.application_id === app.id)} onSaved={onSaved} back={() => navigate('/')} requireAuth={() => setAuth(true)}/> : pathname === '/profile' ? <ProfileEditor key={user?.id || 'guest'} profile={profile} onSaved={setProfile} requireAuth={() => setAuth(true)}/> : pathname === '/drafts' ? <><div className="page-heading"><div><span className="eyebrow">A LITTLE PROGRESS, EVERY DAY</span><h1>My activity<span className="heading-dot">.</span></h1><p className="muted">Pick up where you left off.</p></div></div>{drafts.length ? <div className="activity-list">{drafts.map(d => { const a = applications.find(a => a.id === d.application_id); return a && <button className="activity-row" key={d.application_id} onClick={() => navigate(`/apply/${a.id}`)}><span className={`company-logo logo-${a.platform.toLowerCase()}`}>{a.company.slice(0,1)}</span><div><strong>{a.title}</strong><small>{a.company} · {a.platform}</small></div><span className={`badge ${d.status === 'submitted' ? 'green' : ''}`}>{d.status === 'submitted' ? 'Simulation complete' : 'Draft'}</span><ArrowRight size={17}/></button> })}</div> : <div className="empty-state"><FileText size={32}/><h2>A fresh start.</h2><p>Your saved drafts and completed simulations will appear here.</p><button className="button primary" onClick={() => navigate('/')}>Explore applications <ArrowRight size={16}/></button></div>}</> : pathname === '/about' ? <section className="panel about"><span className="eyebrow">HOW IT WORKS</span><h1>One profile. Room to practice.</h1><p>Create an account, add your candidate information, and upload a resume. Explore 20 fictional opportunities with Workday, Greenhouse, Lever, and other form layouts.</p><p>Use “Fill from my profile” to copy exact stored facts into a form. This feature uses deterministic matching. Ambiguous information and questions you have not verified remain unanswered.</p><p>Save drafts, review every answer, and explicitly approve simulated submissions. These pages are independent simulations, with no affiliation to the named application platforms.</p><p>The Python browser agent remains available as a separate local tool; the website’s profile-fill button does not run a vision model.</p></section> : <Catalog profile={profile} drafts={drafts} signedIn={Boolean(user)} signIn={() => setAuth(true)}/>}
    {auth && <Auth close={() => setAuth(false)}/>}
    {recovery && <div className="modal-backdrop"><section className="modal" role="dialog" aria-modal="true" aria-labelledby="reset-title"><h2 id="reset-title">Choose a new password.</h2><form onSubmit={e => { e.preventDefault(); void supabase?.auth.updateUser({ password: newPassword }).then(({ error }) => { if (error) setError(error.message); else { setRecovery(false); setNewPassword('') } }) }}><label>New password<input type="password" minLength={8} required value={newPassword} onChange={e => setNewPassword(e.target.value)}/></label><button className="button primary full">Update password</button></form></section></div>}
  </Workspace>
}

function Catalog({ profile, drafts, signedIn, signIn }: { profile: CandidateProfile; drafts: Draft[]; signedIn: boolean; signIn: () => void }) {
  const { navigate } = useDashboardNavigation()
  const [platform, setPlatform] = useState<Platform | 'All applications'>('All applications')
  const [query, setQuery] = useState('')
  const [sort, setSort] = useState(false)
  const profileScore = Math.round([Boolean(profile.personal.full_name), Boolean(profile.personal.email), Boolean(profile.education.length), Boolean(profile.work_experience.length), Boolean(profile.skills.length), Boolean(profile.resume)].filter(Boolean).length / 6 * 100)
  const completed = drafts.filter(d => d.status === 'submitted').length
  const shown = applications.filter(a => (platform === 'All applications' || a.platform === platform) && `${a.title} ${a.company} ${a.location}`.toLowerCase().includes(query.toLowerCase())).sort((a,b) => sort ? a.company.localeCompare(b.company) : 0)
  return <><div className="page-heading"><div><span className="eyebrow">SMALL STEPS. NEW POSSIBILITIES.</span><h1>Your next chapter<span className="heading-dot">.</span></h1><p className="muted">A little preparation today. A more confident application tomorrow.</p></div><button className="button secondary" onClick={signedIn ? () => navigate('/profile') : signIn}><UserRound size={16}/>{signedIn ? 'Edit my profile' : 'Create your profile'}<ArrowRight size={15}/></button></div>
  <section className="welcome-card"><div className="welcome-copy"><span className="welcome-label"><span className="tiny-dot"/> YOUR APPLICATION WORKSPACE</span><h2>A good opportunity starts<br/>with a great introduction.</h2><p>Build your profile once. Practice across different application<br className="desktop-break"/> styles, and make every detail count.</p><button className="button cream" onClick={signedIn ? () => navigate('/profile') : signIn}>{signedIn ? 'Complete my profile' : 'Let’s get you ready'}<ArrowRight size={17}/></button></div><div className="welcome-art" aria-hidden="true"><div className="orbit orbit-one"/><div className="orbit orbit-two"/><div className="floating-card card-back"><div className="fake-line"/><div className="fake-line short"/><span>YOUR NEXT OPPORTUNITY</span></div><div className="floating-card card-front"><div className="art-avatar">✳</div><div><strong>Your story.</strong><small>Ready for what’s next.</small></div><div className="art-progress"><i/></div><span><Check size={12}/> A little more prepared.</span></div><span className="art-spark spark-one">✧</span><span className="art-spark spark-two">✳</span></div></section>
  <div className="stats-grid"><div className="stat"><span className="stat-icon"><BriefcaseBusiness size={19}/></span><div><small>Practice opportunities</small><strong>20 <span>across 4 platforms</span></strong></div></div><div className="stat"><span className="stat-icon"><UserRound size={19}/></span><div><small>Your profile</small><strong>{profileScore}% <span>complete</span></strong></div><div className="mini-progress"><i style={{width:`${profileScore}%`}}/></div></div><div className="stat"><span className="stat-icon"><FileText size={19}/></span><div><small>Applications in progress</small><strong>{drafts.length - completed} <span>{completed} completed</span></strong></div></div></div>
  <div className="catalog-heading"><div><h2>Find your practice ground</h2><p>Realistic forms. Fictional companies. A place to get comfortable.</p></div><span className="badge"><ShieldCheck size={13}/> All applications are simulations</span></div>
  <div className="catalog-controls"><div className="platform-tabs" role="tablist" aria-label="Application platform">{(['All applications','Workday','Greenhouse','Lever','Other'] as const).map(p => <button role="tab" aria-selected={platform === p} key={p} onClick={() => setPlatform(p)}>{p}<span>{p === 'All applications' ? 20 : 5}</span></button>)}</div><div className="search-row"><label className="search"><Search size={17}/><input aria-label="Search applications" placeholder="Search roles, companies, locations…" value={query} onChange={e => setQuery(e.target.value)}/></label><button className="button secondary small" aria-pressed={sort} onClick={() => setSort(!sort)}><ArrowDownUp size={14}/>{sort ? 'Company A–Z' : 'Default order'}</button></div></div>
  <div className="result-count">{shown.length} opportunities <span>Make your next move a little easier.</span></div><div className="jobs-grid">{shown.map(a => <article className="job-card" key={a.id}><div className="job-top"><span className={`company-logo logo-${a.platform.toLowerCase()}`}>{a.company.slice(0,1)}<span>·</span></span><span className={`platform-label platform-${a.platform.toLowerCase()}`}>{a.platform}</span></div><p className="company-name">{a.company}</p><h3>{a.title}</h3><p className="job-location">{a.location}</p><div className="job-tags"><span>Full-time</span><span>{a.salary}</span></div><div className="job-bottom"><span>{a.platform === 'Workday' ? 'Multi-step form' : a.platform === 'Other' ? 'Custom form' : 'Single-page form'}</span><button aria-label={`Open ${a.title} at ${a.company}`} onClick={() => navigate(`/apply/${a.id}`)}>{drafts.find(d => d.application_id === a.id)?.status === 'submitted' ? 'View result' : 'Open application'}<ArrowRight size={15}/></button></div></article>)}</div>{!shown.length && <div className="empty-state"><Search size={28}/><h2>No matches yet.</h2><p>Try another role, company, or location.</p><button className="text-button" onClick={() => { setQuery(''); setPlatform('All applications') }}>Clear filters</button></div>}
  <div className="bottom-note"><Sparkles size={16}/><p>A little practice goes a long way. Your next opportunity is worth preparing for.</p></div></>
}
export default function App() { return <DashboardNavigationProvider><Content/></DashboardNavigationProvider> }
