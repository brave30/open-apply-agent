// Adapted from Watermelon UI Agndex Dashboard (MIT). See THIRD_PARTY_NOTICES.md.
import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type AnchorHTMLAttributes,
  type MouseEvent,
  type ReactNode,
} from 'react'

type DashboardNavigation = {
  pathname: string
  navigate: (pathname: string) => void
}

const DashboardNavigationContext = createContext<DashboardNavigation | null>(
  null,
)

export function DashboardNavigationProvider({
  children,
}: {
  children: ReactNode
}) {
  const [pathname, setPathname] = useState(() => window.location.hash.slice(1) || '/')
  useEffect(() => {
    const update = () => setPathname(window.location.hash.slice(1) || '/')
    window.addEventListener('hashchange', update)
    return () => window.removeEventListener('hashchange', update)
  }, [])
  const value = useMemo(
    () => ({ pathname, navigate: (path: string) => { window.location.hash = path; setPathname(path); window.scrollTo(0, 0) } }),
    [pathname],
  )

  return (
    <DashboardNavigationContext.Provider value={value}>
      {children}
    </DashboardNavigationContext.Provider>
  )
}

export function useDashboardNavigation() {
  const context = useContext(DashboardNavigationContext)

  if (!context) {
    throw new Error(
      'useDashboardNavigation must be used within DashboardNavigationProvider',
    )
  }

  return context
}

export function DashboardLink({
  href,
  onClick,
  ...props
}: AnchorHTMLAttributes<HTMLAnchorElement> & { href: string }) {
  const { navigate } = useDashboardNavigation()

  function handleClick(event: MouseEvent<HTMLAnchorElement>) {
    onClick?.(event)

    if (
      event.defaultPrevented ||
      event.button !== 0 ||
      event.metaKey ||
      event.ctrlKey ||
      event.shiftKey ||
      event.altKey
    ) {
      return
    }

    event.preventDefault()
    navigate(href)
  }

  return <a href={`#${href}`} onClick={handleClick} {...props} />
}
