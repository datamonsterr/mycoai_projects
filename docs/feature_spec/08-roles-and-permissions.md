# Feature Spec: Roles and Permissions

## Overview

Two roles control access: **User** and **Data Owner**. Authentication is required for all protected workflows. Data Owner has all User capabilities plus governance capabilities.

## Roles

### Data Owner

**Full access to retrieval, feedback, data management, model/index maintenance, and user management.**

**Permissions:**

| Area | Access |
|------|--------|
| Upload images for retrieval | Yes |
| View retrieval results | Yes |
| Submit feedback or contribution proposal | Yes |
| Index new reference data | Yes |
| Create/edit/archive Species | Yes |
| Create/edit/archive Media | Yes |
| Browse/search/filter/group dataset | Yes |
| Update image metadata | Yes |
| Archive/restore dataset records | Yes |
| Review feedback (accept/reject/defer) | Yes |
| Re-index Qdrant | Yes |
| Review external retraining guidance | Yes |
| Upload/assess/promote Candidate Model | Yes |
| View audit logs | Yes |
| Manage users and roles | Yes |

### User

**Retrieval and feedback only. Cannot browse or mutate the reference dataset.**

**Permissions:**

| Area | Access |
|------|--------|
| Upload images for retrieval | Yes |
| View retrieval results | Yes |
| Submit feedback from retrieval results | Yes |
| Submit contribution proposal from retrieval results | Yes |
| Download batch retrieval results | Yes |
| Browse reference dataset | No |
| Create/edit Species | No |
| Create/edit Media | No |
| Index new reference data | No |
| Archive/restore dataset records | No |
| Review feedback | No |
| Re-index Qdrant | No |
| Upload/assess/promote Candidate Model | No |
| View audit logs | No |
| Manage users | No |

## User Stories

### 1. Registration and Login

**As a** User
**I want** to create an account and log in
**So that** I can use retrieval workflows

**Behavior:**
- Self-registration remains available for Users: email + password + name
- Login: email + password, authenticated session
- Profile: name, email, role
- Initial Data Owner is provisioned internally by script using user email
- Data Owner can invite Users by onboarding email for convenience

### 2. Role Assignment

**As a** Data Owner
**I want** to assign and revoke roles
**So that** I can control who governs the dataset

**Behavior:**
- Data Owners can promote Users to Data Owner
- Data Owners can demote Data Owners
- System must keep at least one active Data Owner
- Role changes are logged in audit trail

### 3. Permission Enforcement

**As a** system
**I want** to enforce role-based permissions on all endpoints
**So that** unauthorized actions are blocked

**Behavior:**
- Backend validates user role on every protected endpoint
- User accessing Data Owner endpoints receives 403 Forbidden
- Unauthenticated actor receives 401 Unauthorized
- UI hides unavailable actions based on role
- API returns 403 even if UI is bypassed

## Resolved Decisions

1. Canonical actor term is **User**, not "Normal User".
2. There is no contributor role. User contribution happens through feedback review.
3. Users cannot browse the reference dataset. Feedback is only available from retrieval results.
4. Initial Data Owner is created by internal script; role promotion is available afterward.

## Acceptance Criteria

- [ ] User self-registration with email/password
- [ ] Login with session management
- [ ] Data Owner invitation with onboarding email
- [ ] Initial Data Owner provisioning by script
- [ ] Role-based UI hiding unavailable actions
- [ ] Role-based API enforcement with 401/403 responses
- [ ] Data Owner can promote/demote roles
- [ ] At least one active Data Owner must exist
- [ ] Audit log of role changes
- [ ] User cannot browse reference dataset endpoints

## Dependencies

- All other feature specs (enforces access boundaries)
- `../SRS.md` UC-001 and UC-006
