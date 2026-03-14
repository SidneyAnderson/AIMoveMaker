import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'
import LoginView from '@/views/LoginView'
import ChangePasswordView from '@/views/ChangePasswordView'
import AppShell from '@/components/AppShell'
import AdminView from '@/views/AdminView'
import StoryboardView from '@/views/StoryboardView'
import TimelineView from '@/views/TimelineView'
import SettingsView from '@/views/SettingsView'
import ProjectsView from '@/views/ProjectsView'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((s) => s.accessToken)
  const user = useAuthStore((s) => s.user)
  if (!token) return <Navigate to="/login" replace />
  // Force password change redirect
  if (user?.force_password_change) return <Navigate to="/change-password" replace />
  return <>{children}</>
}

function AuthRequired({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((s) => s.accessToken)
  if (!token) return <Navigate to="/login" replace />
  return <>{children}</>
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginView />} />
      <Route
        path="/change-password"
        element={
          <AuthRequired>
            <ChangePasswordView />
          </AuthRequired>
        }
      />
      <Route
        path="/*"
        element={
          <ProtectedRoute>
            <AppShell>
              <Routes>
                <Route path="/" element={<ProjectsView />} />
                <Route path="/projects" element={<ProjectsView />} />
                <Route path="/projects/:projectId/storyboard" element={<StoryboardView />} />
                <Route path="/projects/:projectId/timeline" element={<TimelineView />} />
                <Route path="/admin" element={<AdminView />} />
                <Route path="/settings" element={<SettingsView />} />
              </Routes>
            </AppShell>
          </ProtectedRoute>
        }
      />
    </Routes>
  )
}
