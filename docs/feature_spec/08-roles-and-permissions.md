# Feature Spec: Roles and Permissions

## Overview

Two user roles control access to features: Data Owner and Normal User.
Authentication is required for all data-modifying operations.

## Roles

### Data Owner

**Full access to data management and system configuration.**

**Permissions:**

| Area | Access |
|------|--------|
| Upload images for classification | Yes |
| View retrieval results | Yes |
| Submit feedback | Yes |
| Create/edit species | Yes |
| Upload images with direct species link | Yes |
| Update species names | Yes |
| Archive/delete data | Yes |
| Restore from trash | Yes |
| Review feedback (accept/reject) | Yes |
| Trigger retraining | Yes |
| Configure system settings | Yes |
| View audit logs | Yes |
| Manage users | Yes |

### Normal User

**Classification and feedback only. Cannot modify database.**

**Permissions:**

| Area | Access |
|------|--------|
| Upload images for classification | Yes |
| View retrieval results | Yes |
| Submit feedback | Yes |
| Submit feedback on database entries | Yes |
| Create/edit species | No |
| Upload images with direct species link | No |
| Update species names | No |
| Archive/delete data | No |
| Restore from trash | No |
| Review feedback | No |
| Trigger retraining | No |
| Configure system settings | No |
| View audit logs | No |

## User Stories

### 1. Registration and Login

**As a** researcher
**I want** to create an account and log in
**So that** I can use the classification system

**Behavior:**
- Registration: email + password + name
- Account activation: auto-activate or email verification (configurable)
- Login: email + password, JWT session
- Profile: name, email, role (display only)

### 2. Role Assignment

**As a** data owner
**I want** to assign and revoke roles
**So that** I can control who manages the database

**Behavior:**
- First registered user is automatically Data Owner
- Data owners can promote other users to Data Owner
- Data owners can demote other Data Owners (must keep at least one)
- Role changes are logged in audit trail

### 3. Permission Enforcement

**As a** system
**I want** to enforce role-based permissions on all endpoints
**So that** unauthorized actions are blocked

**Behavior:**
- Backend validates user role on every protected endpoint
- Normal user accessing data-owner endpoints receives 403 Forbidden
- Unauthenticated user receives 401 Unauthorized
- UI hides unavailable actions (buttons, menus) based on role
- API returns 403 even if UI is bypassed

## Open Questions

1. Can normal users add data to the database by asking permission from the
   data owner? (Spec says: data owner can approve, making it a
   feedback-accept workflow — see 05-feedback-pipeline.md)
2. Should there be a "contributor" role between Normal User and Data Owner?
3. Is anonymous/public access needed for any endpoints (e.g., species list)?

## Acceptance Criteria

- [ ] User registration with email/password
- [ ] Login with JWT session management
- [ ] Role-based UI (hide unavailable actions)
- [ ] Role-based API enforcement (401/403 responses)
- [ ] First user auto-assigned as Data Owner
- [ ] Data Owner can manage other users' roles
- [ ] Audit log of role changes
- [ ] At least one Data Owner must exist at all times

## Dependencies

- All other feature specs (enforces access boundaries)
