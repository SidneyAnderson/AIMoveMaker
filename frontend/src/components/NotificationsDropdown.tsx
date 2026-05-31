import { useState } from 'react'
import { Bell, CheckCheck, ExternalLink } from 'lucide-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { listNotifications, markRead, markAllRead, Notification } from '@/api/notifications'
import { toast } from 'sonner'
import { useNavigate } from 'react-router-dom'
import { useWebSocket } from '@/hooks/useWebSocket'
import { useAuthStore } from '@/stores/authStore'

export default function NotificationsDropdown() {
  const [open, setOpen] = useState(false)
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const currentUserId = useAuthStore((s) => s.user?.id)

  // Real-time WS push for notifications (advanced)
  useWebSocket({
    url: `/ws/notifications${currentUserId ? `?user_id=${currentUserId}` : ''}`,
    onMessage: (data: any) => {
      if (data?.type === 'notification') {
        queryClient.invalidateQueries({ queryKey: ['notifications'] })
        // Optional: show toast for new notif when panel closed
        if (!open && data.notification) {
          toast.info(`New: ${String(data.notification.type || 'notification').replace(/_/g, ' ')}`)
        }
      }
    },
    enabled: true,
  })

  const { data, isLoading } = useQuery({
    queryKey: ['notifications'],
    queryFn: listNotifications,
    enabled: open,
  })

  const notifications: Notification[] = data?.items || []
  const unreadCount = notifications.filter((n) => !n.read_at).length

  const markReadMutation = useMutation({
    mutationFn: (id: string) => markRead(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
    },
  })

  const markAllMutation = useMutation({
    mutationFn: markAllRead,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
      toast.success('All notifications marked as read')
    },
  })

  const handleNotificationClick = (notif: Notification) => {
    markReadMutation.mutate(notif.id)
    setOpen(false)

    // Navigate based on payload if available (advanced feature)
    if (notif.payload?.project_id) {
      navigate(`/projects/${notif.payload.project_id}/storyboard`)
    } else if (notif.payload?.job_id) {
      // Could open jobs panel or project jobs
      toast.info('Job notification - check the project timeline or jobs view')
    }
  }

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="text-text-muted hover:text-text-primary relative p-2"
        aria-label="Notifications"
      >
        <Bell className="w-4 h-4" />
        {unreadCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 bg-error text-white text-[10px] rounded-full px-1 min-w-[14px] text-center">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-80 bg-bg-elevated border border-border rounded-card shadow-2xl z-50 overflow-hidden">
          <div className="flex items-center justify-between px-4 py-2 border-b border-border bg-bg-surface">
            <span className="font-medium text-sm">Notifications</span>
            {unreadCount > 0 && (
              <button
                onClick={() => markAllMutation.mutate()}
                className="text-xs text-accent hover:underline flex items-center gap-1"
                disabled={markAllMutation.isPending}
              >
                <CheckCheck className="w-3 h-3" /> Mark all read
              </button>
            )}
          </div>

          <div className="max-h-96 overflow-auto">
            {isLoading ? (
              <div className="p-4 text-sm text-text-muted">Loading...</div>
            ) : notifications.length === 0 ? (
              <div className="p-4 text-sm text-text-muted">No notifications yet.</div>
            ) : (
              notifications.map((notif) => (
                <div
                  key={notif.id}
                  onClick={() => handleNotificationClick(notif)}
                  className={`px-4 py-3 border-b border-border last:border-b-0 cursor-pointer hover:bg-bg-subtle text-sm ${
                    !notif.read_at ? 'bg-accent-subtle/30' : ''
                  }`}
                >
                  <div className="flex justify-between">
                    <span className="font-medium text-text-primary">{notif.type.replace(/_/g, ' ')}</span>
                    <span className="text-[10px] text-text-muted">
                      {new Date(notif.created_at).toLocaleDateString()}
                    </span>
                  </div>
                  {notif.payload && (
                    <div className="text-xs text-text-secondary mt-0.5 truncate">
                      {JSON.stringify(notif.payload).slice(0, 80)}...
                    </div>
                  )}
                  <div className="text-[10px] text-text-muted mt-1 flex items-center gap-1">
                    {notif.channel} • {notif.read_at ? 'read' : 'unread'}
                    {notif.payload?.project_id && <ExternalLink className="w-3 h-3" />}
                  </div>
                </div>
              ))
            )}
          </div>

          <div className="px-4 py-2 text-xs border-t border-border bg-bg-surface text-center text-text-muted">
            Notifications update in real-time via WebSocket (advanced)
          </div>
        </div>
      )}
    </div>
  )
}
