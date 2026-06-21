# Bug 008: Invite user via email does not work

**Status:** CONFIRMED | **Severity:** High | **Component:** Backend + Frontend

## Root Cause

Complete no-op. The invite flow is dysfunctional at every layer.

**Frontend** (`frontend/src/pages/UserManagement.tsx:182-195`):
- "Send Invitation" button `onClick` only closes dialog: `() => setInviteOpen(false)`
- No API call, no data sent, no email triggered
- Email input not connected to state (no `useState`, no `value`/`onChange`)

**Backend:**
- No invite endpoint exists (grep "invite" across `backend/src/` = zero results)
- No email-sending mechanism (no SMTP config, no SendGrid, no mail module)
- Registration endpoint (`api/auth.py:40-48`) accepts direct signup — no invite token flow

## What's Missing

1. Backend invite endpoint (`POST /admin/users/invite`)
2. Email service/infrastructure (SMTP settings, mailer)
3. Invite token generation + validation
4. Frontend form state management for email input
5. Frontend API call to invite endpoint

## Solution

**Backend:**
1. Add `POST /admin/users/invite` — creates user with `is_active=False`, invite token, sends email
2. Add email service (SMTP in `config.py`, email template)
3. Add `POST /auth/register-with-token` — validates token, activates user

**Frontend:**
```tsx
const [inviteEmail, setInviteEmail] = useState('')
// <Input value={inviteEmail} onChange={(e) => setInviteEmail(e.target.value)} />
// <Button onClick={() => inviteMutation.mutate(inviteEmail)}>Send Invitation</Button>
```

## Files to Modify

- `backend/src/api/admin.py` — add invite endpoint
- `backend/src/api/auth.py` — add register-with-token endpoint
- `backend/src/core/config.py` — add email/SMTP settings
- `backend/src/schemas/admin.py` — add InviteRequest schema
- `frontend/src/pages/UserManagement.tsx` — wire input + API call
- `frontend/src/services/admin.ts` — add invite API function
