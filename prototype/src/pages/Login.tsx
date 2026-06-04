import { useState } from 'react'
import { useAuth } from '@/lib/use-auth'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { FlaskConical } from 'lucide-react'
import { users } from '@/lib/mock-data'

export default function LoginPage() {
  const { login } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [mode, setMode] = useState<'login' | 'register'>('login')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    if (mode === 'login') {
      const ok = login(email, password)
      if (!ok) setError('Invalid credentials or inactive account.')
    } else {
      setError('Registration successful (mock). Switch to login.')
      setMode('login')
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <FlaskConical className="h-10 w-10 text-primary mx-auto mb-2" />
          <CardTitle className="font-heading text-2xl">MycoAI Retrieval</CardTitle>
          <p className="text-sm text-muted-foreground">
            {mode === 'login' ? 'Sign in to your account' : 'Create a new account'}
          </p>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {mode === 'register' && (
              <div className="space-y-2">
                <Label htmlFor="name">Name</Label>
                <Input id="name" placeholder="Your name" required />
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
                minLength={6}
              />
            </div>
            {error && <p className="text-sm text-destructive">{error}</p>}
            <Button type="submit" className="w-full">
              {mode === 'login' ? 'Sign In' : 'Register'}
            </Button>
          </form>
          <div className="mt-4 space-y-2">
            <button
              type="button"
              className="text-xs text-muted-foreground hover:text-foreground cursor-pointer w-full text-center"
              onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError('') }}
            >
              {mode === 'login' ? "Don't have an account? Register" : 'Already have an account? Sign In'}
            </button>
            <div className="border-t border-border pt-2">
              <p className="text-xs text-muted-foreground mb-2 text-center">Quick demo logins:</p>
              <div className="space-y-1">
                {users.filter(u => u.account_status === 'active').map((u) => (
                  <button
                    key={u.user_id}
                    type="button"
                    className="w-full text-left text-xs px-3 py-1.5 rounded hover:bg-muted cursor-pointer flex justify-between"
                    onClick={() => { setEmail(u.email); setPassword('password'); }}
                  >
                    <span>{u.name}</span>
                    <span className="text-muted-foreground">{u.role === 'owner' ? 'Data Owner' : 'User'}</span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
