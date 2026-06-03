import { cn } from '@/lib/utils'
import { useAuth } from '@/lib/use-auth'
import { useMemo } from 'react'
import type { Role } from '@/lib/mock-data'
import { feedbackItems } from '@/lib/mock-data'
import {
  LayoutDashboard,
  Upload,
  Search,
  MessageSquareText,
  Database,
  Tags,
  Users,
  FileText,
  LogOut,
  Menu,
  X,
  Shield,
  FlaskConical,
  PanelLeftClose,
  PanelLeftOpen,
  type LucideIcon,
} from 'lucide-react'
import { useState } from 'react'

interface NavItem {
  label: string
  href: string
  icon: LucideIcon
  roles: Role[]
  badge?: number
}

const userNav: NavItem[] = [
  { label: 'Retrieve Species', href: '/retrieve', icon: Search, roles: ['user', 'owner'] },
  { label: 'My Feedback', href: '/my-feedback', icon: MessageSquareText, roles: ['user', 'owner'] },
]

const ownerNav: NavItem[] = [
  { label: 'Dashboard', href: '/dashboard', icon: LayoutDashboard, roles: ['owner'] },
  { label: 'Retrieve Species', href: '/retrieve', icon: Search, roles: ['owner'] },
  { label: 'Index New Data', href: '/index', icon: Upload, roles: ['owner'] },
  { label: 'Dataset Browser', href: '/dataset', icon: Database, roles: ['owner'] },
  { label: 'Manage Metadata', href: '/metadata', icon: Tags, roles: ['owner'] },
  { label: 'Feedback Inbox', href: '/feedback-inbox', icon: MessageSquareText, roles: ['owner'] },
  { label: 'Model & Index', href: '/model', icon: FlaskConical, roles: ['owner'] },
  { label: 'User Management', href: '/users', icon: Users, roles: ['owner'] },
  { label: 'Audit Log', href: '/audit', icon: FileText, roles: ['owner'] },
]

export function AppLayout({ children }: { children: React.ReactNode }) {
  const { user, logout, switchRole } = useAuth()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [collapsed, setCollapsed] = useState(false)

  const handleNavigate = (href: string) => {
    setSidebarOpen(false)
    window.history.pushState({}, '', href)
    window.dispatchEvent(new PopStateEvent('popstate'))
  }

  const pathname = window.location.pathname
  const isOwner = user?.role === 'owner'
  const navItems = isOwner ? ownerNav : userNav

  const pendingCount = useMemo(() => feedbackItems.filter((f) => f.status === 'pending').length, [])

  const navWithBadges = navItems.map((item) => {
    if (item.href === '/feedback-inbox' && isOwner && pendingCount > 0) {
      return { ...item, badge: pendingCount }
    }
    if (item.href === '/my-feedback' && !isOwner && pendingCount > 0) {
      const myPending = feedbackItems.filter((f) => f.status === 'pending' && f.submitter_id === user?.user_id).length
      if (myPending > 0) return { ...item, badge: myPending }
    }
    return item
  })

  return (
    <div className="flex min-h-screen bg-background">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-40 bg-black/50 lg:hidden" onClick={() => setSidebarOpen(false)} />
      )}

      {/* Sidebar */}
      <aside className={cn(
        'fixed inset-y-0 left-0 z-50 border-r border-border bg-card flex flex-col transition-all duration-200',
        collapsed ? 'w-16' : 'w-64',
        'lg:relative lg:translate-x-0',
        sidebarOpen ? 'translate-x-0' : '-translate-x-full',
      )}>
        <div className="flex items-center h-14 px-3 border-b border-border">
          {!collapsed && (
            <div className="flex items-center gap-2 flex-1 min-w-0">
              <FlaskConical className="h-5 w-5 text-primary flex-shrink-0" />
              <span className="font-heading font-bold text-foreground text-lg truncate">MycoAI</span>
            </div>
          )}
          {collapsed && (
            <FlaskConical className="h-5 w-5 text-primary mx-auto" />
          )}
          <button
            className={cn('cursor-pointer hover:bg-muted rounded-md p-1.5 transition-colors hidden lg:flex', collapsed ? 'mx-auto mt-0' : '')}
            onClick={() => setCollapsed(!collapsed)}
            title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {collapsed ? <PanelLeftOpen className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}
          </button>
          <button className="lg:hidden cursor-pointer hover:bg-muted rounded-md p-1.5" onClick={() => setSidebarOpen(false)}>
            <X className="h-5 w-5" />
          </button>
        </div>

        <nav className="flex-1 overflow-y-auto p-2 space-y-1">
          {navWithBadges.map((item) => {
            const isActive = pathname === item.href || (item.href !== '/' && pathname.startsWith(item.href))
            return (
              <a
                key={item.href}
                href={item.href}
                className={cn(
                  'flex items-center rounded-md text-sm font-medium transition-colors relative group',
                  collapsed ? 'justify-center px-2 py-2.5' : 'gap-3 px-3 py-2',
                  isActive
                    ? 'bg-primary text-primary-foreground'
                    : 'text-foreground hover:bg-muted',
                )}
                onClick={(e) => { e.preventDefault(); handleNavigate(item.href) }}
                title={collapsed ? item.label : undefined}
              >
                <item.icon className={cn('h-4 w-4 flex-shrink-0', collapsed && 'h-5 w-5')} />
                {!collapsed && <span className="flex-1 truncate">{item.label}</span>}
                {item.badge != null && item.badge > 0 && (
                  <span className={cn(
                    'inline-flex items-center justify-center min-w-[20px] h-5 rounded-full bg-destructive px-1.5 text-[10px] font-bold text-destructive-foreground',
                    collapsed && 'absolute -top-0.5 -right-0.5 min-w-[16px] h-4 text-[9px] px-1',
                  )}>
                    {item.badge}
                  </span>
                )}
                {/* Tooltip on hover when collapsed */}
                {collapsed && (
                  <span className="absolute left-full ml-2 px-2 py-1 rounded-md bg-foreground text-background text-xs whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none z-50 transition-opacity">
                    {item.label}{item.badge != null && item.badge > 0 ? ` (${item.badge})` : ''}
                  </span>
                )}
              </a>
            )
          })}
        </nav>

        <div className={cn('border-t border-border', collapsed ? 'p-2' : 'p-4 space-y-2')}>
          {collapsed ? (
            <div className="flex justify-center" title={user?.name}>
              <div className="h-8 w-8 rounded-full bg-primary flex items-center justify-center text-primary-foreground text-xs font-bold font-heading">
                {user?.name.split(' ').map((n) => n[0]).join('')}
              </div>
            </div>
          ) : (
            <>
              <div className="flex items-center gap-3">
                <div className="h-8 w-8 rounded-full bg-primary flex items-center justify-center text-primary-foreground text-xs font-bold font-heading">
                  {user?.name.split(' ').map((n) => n[0]).join('')}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{user?.name}</p>
                  <p className="text-xs text-muted-foreground">{user?.role === 'owner' ? 'Data Owner' : 'User'}</p>
                </div>
              </div>
              <div className="flex gap-1">
                <button
                  onClick={() => switchRole(user?.role === 'owner' ? 'user' : 'owner')}
                  className="flex-1 inline-flex items-center justify-center gap-1 rounded-md border border-border px-2 py-1 text-xs cursor-pointer hover:bg-muted transition-colors"
                >
                  <Shield className="h-3 w-3" />
                  {user?.role === 'owner' ? 'View as User' : 'View as Owner'}
                </button>
                <button
                  onClick={logout}
                  className="inline-flex items-center justify-center rounded-md border border-border p-1 cursor-pointer hover:bg-muted transition-colors"
                >
                  <LogOut className="h-4 w-4" />
                </button>
              </div>
            </>
          )}
        </div>
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Mobile menu trigger */}
        <button
          className="lg:hidden fixed top-3 left-3 z-30 h-9 w-9 flex items-center justify-center rounded-md border border-border bg-card shadow-sm cursor-pointer"
          onClick={() => setSidebarOpen(true)}
        >
          <Menu className="h-5 w-5" />
        </button>
        <main className="flex-1 p-4 pt-14 lg:pt-4 lg:p-6 max-w-7xl w-full mx-auto">
          {children}
        </main>
      </div>
    </div>
  )
}
