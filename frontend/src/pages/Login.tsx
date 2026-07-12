import { useMemo, useState } from 'react'
import { useAuth } from '@/lib/use-auth'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { FlaskConical } from 'lucide-react'

export default function LoginPage() {
  const { login } = useAuth()
  const params = useMemo(() => new URLSearchParams(window.location.search), [])
  const inviteToken = params.get('token')?.trim() ?? ''
  const inviteEmail = params.get('email')?.trim() ?? ''
  const isInviteFlow = inviteToken.length > 0 && inviteEmail.length > 0
  const [email, setEmail] = useState(inviteEmail)
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [mode, setMode] = useState<'login' | 'register'>(isInviteFlow ? 'register' : 'login')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    if (mode === 'login') {
      const ok = await login(email, password)
      if (!ok) {
        setError('Invalid credentials or inactive account.')
      } else {
        const params = new URLSearchParams(window.location.search)
        const next = params.get('next') || '/retrieve'
        window.location.assign(next)
      }
    } else {
      try {
        const { authService } = await import('@/services/auth')
        if (isInviteFlow) {
          await authService.registerWithToken({ email, password, name, token: inviteToken })
        } else {
          await authService.register({ email, password, name })
        }
        const ok = await login(email, password)
        if (!ok) setError('Registration succeeded but login failed. Please try signing in.')
        else setMode('login')
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : 'Registration failed. Please try again.')
      }
    }
    setLoading(false)
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <FlaskConical className="h-10 w-10 text-primary mx-auto mb-2" />
          <CardTitle className="font-heading text-2xl">MycoAI Retrieval</CardTitle>
          <p className="text-sm text-muted-foreground">
            {mode === 'login' ? 'Sign in to your account' : isInviteFlow ? 'Complete your invited account setup' : 'Create a new account'}
          </p>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {mode === 'register' && (
              <div className="space-y-2">
                <Label htmlFor="name">Name</Label>
                <Input id="name" placeholder="Your name" value={name} onChange={(e) => setName(e.target.value)} required />
              </div>
            )}
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="user@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                readOnly={isInviteFlow}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={8}
              />
            </div>
            {error && <p className="text-sm text-destructive">{error}</p>}
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? 'Please wait...' : mode === 'login' ? 'Sign In' : 'Register'}
            </Button>
          </form>
          {!isInviteFlow && (
            <div className="mt-4">
              <button
                type="button"
                className="text-xs text-muted-foreground hover:text-foreground cursor-pointer w-full text-center"
                onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError('') }}
              >
                {mode === 'login' ? "Don't have an account? Register" : 'Already have an account? Sign In'}
              </button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
