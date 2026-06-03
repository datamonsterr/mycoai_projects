import { useState, useEffect } from 'react'
import { AuthProvider } from '@/lib/auth'
import { useAuth } from '@/lib/use-auth'
import { AppLayout } from '@/components/layout'
import LoginPage from '@/pages/Login'
import DashboardPage from '@/pages/Dashboard'
import RetrievePage from '@/pages/Retrieve'
import MyFeedbackPage from '@/pages/MyFeedback'
import IndexNewDataPage from '@/pages/IndexNewData'
import DatasetPage from '@/pages/Dataset'
import MetadataPage from '@/pages/Metadata'
import FeedbackInboxPage from '@/pages/FeedbackInbox'
import ModelIndexPage from '@/pages/ModelIndex'
import UserManagementPage from '@/pages/UserManagement'
import AuditLogPage from '@/pages/AuditLog'

function Router() {
  const { user } = useAuth()
  const [path, setPath] = useState(window.location.pathname)

  useEffect(() => {
    const handler = () => setPath(window.location.pathname)
    window.addEventListener('popstate', handler)
    return () => window.removeEventListener('popstate', handler)
  }, [])

  if (!user) return <LoginPage />

  const isOwner = user.role === 'owner'

  const renderPage = () => {
    switch (path) {
      case '/': return <DashboardPage />
      case '/dashboard': return isOwner ? <DashboardPage /> : <RetrievePage />
      case '/retrieve': return <RetrievePage />
      case '/my-feedback': return <MyFeedbackPage />
      case '/index': return isOwner ? <IndexNewDataPage /> : <RetrievePage />
      case '/dataset': return isOwner ? <DatasetPage /> : <RetrievePage />
      case '/metadata': return isOwner ? <MetadataPage /> : <RetrievePage />
      case '/feedback-inbox': return isOwner ? <FeedbackInboxPage /> : <MyFeedbackPage />
      case '/model': return isOwner ? <ModelIndexPage /> : <RetrievePage />
      case '/users': return isOwner ? <UserManagementPage /> : <RetrievePage />
      case '/audit': return isOwner ? <AuditLogPage /> : <RetrievePage />
      default: return <RetrievePage />
    }
  }

  return <AppLayout>{renderPage()}</AppLayout>
}

export default function App() {
  return (
    <AuthProvider>
      <Router />
    </AuthProvider>
  )
}
