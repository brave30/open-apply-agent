import { ArrowUpRight, BriefcaseBusiness, CircleHelp, FileText, LogOut, Sprout, UserRound } from 'lucide-react'
import type { ReactNode } from 'react'
import { DashboardLink, useDashboardNavigation } from './navigation'

// Sidebar grouping, active-link behavior and content shell adapted from
// Watermelon UI's Agndex Dashboard. See THIRD_PARTY_NOTICES.md.
export function Workspace({ children, email, signOut }: { children: ReactNode; email?: string; signOut: () => void }) {
  const { pathname } = useDashboardNavigation()
  const items = [{ href: '/', name: 'Applications', icon: BriefcaseBusiness }, { href: '/profile', name: 'My profile', icon: UserRound }, { href: '/drafts', name: 'My activity', icon: FileText }]
  return <div className="workspace"><aside className="sidebar">
    <DashboardLink href="/" className="brand"><span className="brand-mark"><Sprout size={22}/></span>open apply<span className="beta">BETA</span></DashboardLink>
    <div className="workspace-label"><span className="tiny-dot"/> Candidate workspace</div>
    <div className="nav-caption">WORKSPACE</div>
    <nav aria-label="Main navigation">{items.map(item => <DashboardLink key={item.href} href={item.href} className="nav-item" aria-current={(item.href === '/' ? pathname === '/' || pathname.startsWith('/apply/') : pathname === item.href) ? 'page' : undefined}><item.icon size={18}/>{item.name}{item.href === '/' && <span className="nav-count">20</span>}</DashboardLink>)}</nav>
    <div className="sidebar-note"><span className="note-icon"><CircleHelp size={18}/></span><h3>A space to practice.</h3><p>Explore application flows and keep your candidate details in one place.</p><DashboardLink href="/about">How it works <ArrowUpRight size={14}/></DashboardLink></div>
    <div className="account"><span className="avatar">{email?.slice(0, 2).toUpperCase() || 'OA'}</span><div><strong>{email ? 'Personal account' : 'Preview workspace'}</strong><small>{email || 'Sign in to save your profile'}</small></div>{email && <button className="icon-button" aria-label="Sign out" onClick={signOut}><LogOut size={17}/></button>}</div>
  </aside><main className="main-shell"><header className="topbar"><span>Workspace <span className="crumb">/</span> <strong>{pathname === '/profile' ? 'My profile' : pathname === '/drafts' ? 'My activity' : pathname.startsWith('/apply/') ? 'Application' : 'Applications'}</strong></span><span className="test-pill"><span className="tiny-dot"/> Simulation environment</span></header><div className="page">{children}</div><footer className="footer">Made for a more thoughtful job search.<span>Open Apply · Application testing workspace</span></footer></main></div>
}
