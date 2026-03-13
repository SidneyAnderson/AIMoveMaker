import { ReactNode, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'
import { useProjectStore } from '@/stores/projectStore'
import {
  Film, FolderKanban, Settings, LogOut, Menu, Search,
  LayoutGrid, Clock, Users, Bell
} from 'lucide-react'
import CommandPalette from './CommandPalette'

interface AppShellProps {
  children: ReactNode
}

export default function AppShell({ children }: AppShellProps) {
  const location = useLocation()
  const navigate = useNavigate()
  const user = useAuthStore((s) => s.user)
  const logout = useAuthStore((s) => s.logout)
  const [cmdOpen, setCmdOpen] = useState(false)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const navItems = [
    { to: '/projects', icon: FolderKanban, label: 'Projects' },
    { to: '/admin', icon: Users, label: 'Admin', adminOnly: true },
    { to: '/settings', icon: Settings, label: 'Settings' },
  ]

  return (
    <div className="flex h-screen overflow-hidden bg-bg-base">
      {/* Left Sidebar */}
      <aside
        className={`flex flex-col border-r border-border bg-bg-surface transition-all ${
          sidebarCollapsed ? 'w-[48px]' : 'w-[220px]'
        }`}
      >
        {/* Logo */}
        <div className="flex items-center gap-2 px-4 py-3 border-b border-border">
          <Film className="w-5 h-5 text-accent" />
          {!sidebarCollapsed && (
            <span className="text-sm font-semibold text-text-primary">AI Movie Maker</span>
          )}
        </div>

        {/* Nav */}
        <nav className="flex-1 py-2">
          {navItems
            .filter((item) => !item.adminOnly || user?.global_role === 'admin')
            .map((item) => {
              const active = location.pathname.startsWith(item.to)
              return (
                <Link
                  key={item.to}
                  to={item.to}
                  className={`flex items-center gap-3 px-4 py-2 text-sm transition-colors ${
                    active
                      ? 'text-accent bg-accent-subtle'
                      : 'text-text-secondary hover:text-text-primary hover:bg-bg-subtle'
                  }`}
                >
                  <item.icon className="w-4 h-4" />
                  {!sidebarCollapsed && item.label}
                </Link>
              )
            })}
        </nav>

        {/* User */}
        <div className="border-t border-border p-3">
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 text-sm text-text-muted hover:text-error w-full"
          >
            <LogOut className="w-4 h-4" />
            {!sidebarCollapsed && 'Logout'}
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top Bar */}
        <header className="h-12 flex items-center justify-between px-4 border-b border-border bg-bg-surface">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
              className="text-text-muted hover:text-text-primary"
            >
              <Menu className="w-4 h-4" />
            </button>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => setCmdOpen(true)}
              className="flex items-center gap-2 text-sm text-text-muted hover:text-text-primary px-3 py-1 rounded-btn border border-border"
            >
              <Search className="w-3 h-3" />
              <span>Search...</span>
              <kbd className="text-xs text-text-muted">⌘K</kbd>
            </button>
            <button className="text-text-muted hover:text-text-primary relative">
              <Bell className="w-4 h-4" />
            </button>
            <span className="text-sm text-text-secondary">
              {user?.full_name || user?.email}
            </span>
          </div>
        </header>

        {/* Canvas */}
        <main className="flex-1 overflow-auto">{children}</main>
      </div>

      {/* Command Palette */}
      <CommandPalette open={cmdOpen} onOpenChange={setCmdOpen} />
    </div>
  )
}
