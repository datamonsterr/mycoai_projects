import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import UserManagementPage from '@/pages/UserManagement'
import { listUsers } from '@/services/admin'

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

const mockUsers = {
  items: [
    {
      id: 'u-001',
      email: 'alice@mycoai.org',
      name: 'Dr. Alice Chen',
      role: 'owner',
      is_active: true,
      created_at: '2025-01-01',
    },
    {
      id: 'u-002',
      email: 'jane@university.edu',
      name: 'Jane Smith',
      role: 'user',
      is_active: true,
      created_at: '2025-02-15',
    },
    {
      id: 'u-005',
      email: 'tom@research.net',
      name: 'Tom Harris',
      role: 'user',
      is_active: false,
      created_at: '2025-04-01',
    },
  ],
  total: 3,
  offset: 0,
  limit: 50,
}

beforeEach(() => {
  vi.restoreAllMocks()
})

describe('listUsers service', () => {
  it('calls GET /admin/users and parses response', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(JSON.stringify(mockUsers), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      }),
    )

    const result = await listUsers()
    expect(result.items).toHaveLength(3)
    expect(result.items[0].name).toBe('Dr. Alice Chen')
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/admin/users'),
      expect.objectContaining({ method: 'GET' }),
    )
  })
})

describe('UserManagement page', () => {
  it('renders user rows after loading', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(JSON.stringify(mockUsers), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      }),
    )

    render(<UserManagementPage />, { wrapper })

    await waitFor(() => {
      expect(screen.getByText('Dr. Alice Chen')).toBeDefined()
    })

    expect(screen.getByText('Jane Smith')).toBeDefined()
    expect(screen.getByText('Tom Harris')).toBeDefined()
  })

  it('shows loading state before data arrives', () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(
      () => new Promise(() => {}), // never resolves
    )

    render(<UserManagementPage />, { wrapper })

    expect(screen.getByText('Loading users...')).toBeDefined()
  })
})
