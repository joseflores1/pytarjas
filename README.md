# Pytarjas API Documentation

A Progressive Web App (PWA) for managing consolidation/deconsolidation tarja forms in field operations.

## Table of Contents
- [Overview](#overview)
- [Architecture](#architecture)
- [Authentication Endpoints](#authentication-endpoints)
- [Admin Endpoints](#admin-endpoints)
- [Tasks API Endpoints](#tasks-api-endpoints)
- [Worker UI Endpoints](#worker-ui-endpoints)
- [Role-Based Access Control](#role-based-access-control)
- [Error Responses](#error-responses)

---

## Overview

**Base URL:** `http://localhost:5000` (development)

**Content Types:**
- HTML forms: `application/x-www-form-urlencoded`
- JSON API: `application/json`

All endpoints support **dual response formats** (HTML and JSON) for maximum flexibility.

---

## Architecture

### Blueprints

| Blueprint | Prefix | Purpose |
|-----------|--------|---------|
| `auth` | `/auth` | Authentication (login, logout, session) |
| `admin` | `/admin` | User management (admin-only) |
| `tasks` | `/tasks` | Task CRUD operations (JSON API) |
| `worker` | `/worker` | Worker dashboard UI (HTML) |

### User Roles

| Role | Permissions |
|------|-------------|
| **admin** | Full system access, user management |
| **worker** | View/update own tasks, fill forms |
| **planner** | View/update all tasks, assign workers |
| **client** | Read-only access to own reports |

---

## Authentication Endpoints

### `POST /auth/login`
Authenticate a user and create a session.

**Request (JSON):**
```json
{
  "username": "worker1",
  "password": "securepass123"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Welcome back, worker1!",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "username": "worker1",
    "role": "worker",
    "email": "worker1@example.com"
  }
}
```

**HTML Form:**
- **GET** `/auth/login` - Display login form
- **POST** `/auth/login` - Submit credentials (redirects on success)

---

### `GET|POST /auth/logout`
End the current user session.

**Response (200 OK):**
```json
{
  "success": true,
  "message": "You have been logged out."
}
```

---

### `GET /auth/session`
Check current authentication status (useful for PWA).

**Response when authenticated (200 OK):**
```json
{
  "authenticated": true,
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "username": "worker1",
    "role": "worker",
    "email": "worker1@example.com"
  }
}
```

**Response when not authenticated (401 Unauthorized):**
```json
{
  "authenticated": false
}
```

---

## Admin Endpoints

**Access:** Admin role required for all endpoints.

### `GET /admin/`
Admin dashboard with user statistics.

**Response (200 OK):**
```json
{
  "success": true,
  "stats": {
    "total": 25,
    "admin": 2,
    "worker": 15,
    "planner": 5,
    "client": 3
  }
}
```

---

### `GET /admin/users`
List all users in the system.

**Query Parameters:**
- `role` (optional): Filter by role (admin, worker, planner, client)

**Example:** `GET /admin/users?role=worker`

**Response (200 OK):**
```json
{
  "success": true,
  "users": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "username": "john_worker",
      "email": "john@example.com",
      "role": "worker",
      "created_at": "2025-01-20T10:30:00+00:00",
      "updated_at": "2025-01-20T14:22:00+00:00",
      "login_at": "2025-01-21T08:15:00+00:00"
    }
  ],
  "count": 1,
  "filter": "worker"
}
```

---

### `GET /admin/users/<user_id>`
Get details for a specific user.

**Response (200 OK):**
```json
{
  "success": true,
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "username": "john_worker",
    "email": "john@example.com",
    "role": "worker",
    "created_at": "2025-01-20T10:30:00+00:00",
    "updated_at": "2025-01-20T14:22:00+00:00",
    "login_at": "2025-01-21T08:15:00+00:00"
  }
}
```

---

### `POST /admin/users/create`
Create a new user.

**Request (JSON):**
```json
{
  "username": "new_worker",
  "email": "newworker@example.com",
  "password": "secure123",
  "password_confirm": "secure123",
  "role": "worker"
}
```

**Response (201 Created):**
```json
{
  "success": true,
  "message": "User 'new_worker' created successfully with role 'worker'.",
  "user": {
    "id": "660e8400-e29b-41d4-a716-446655440000",
    "username": "new_worker",
    "email": "newworker@example.com",
    "role": "worker",
    "updated_at": null
  }
}
```

---

### `POST|PATCH /admin/users/<user_id>/edit`
Update an existing user (supports partial updates).

**Request (JSON) - Partial Update (email only):**
```json
{
  "email": "john.newest@example.com"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "User 'john_worker' updated successfully. Changed: email.",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "username": "john_worker",
    "email": "john.newest@example.com",
    "role": "worker",
    "updated_at": "2025-01-21T09:30:00+00:00"
  }
}
```

**Security Note:** Admins cannot change their own role.

---

### `POST|DELETE /admin/users/<user_id>/delete`
Delete a user from the system.

**Response (200 OK):**
```json
{
  "success": true,
  "message": "User 'john_worker' deleted successfully."
}
```

---

## Tasks API Endpoints

**Access:** Workers, Planners, and Admins only (Clients blocked).

### `GET /tasks/`
List tasks with role-based filtering.

**Query Parameters:**
- `status` (optional): Filter by status (pending, in_progress, completed, reviewed, approved, all)
- `limit` (optional): Max results (default: 50, max: 100)
- `offset` (optional): Pagination offset (default: 0)
- `worker_id` (optional): Filter by worker ID (planner/admin only)
- `container_number` (optional): Search by container number

**Access Control:**
- **Workers:** See only their assigned tasks
- **Planners/Admins:** See all tasks (can filter by worker)

**Example:** `GET /tasks/?status=pending&limit=20`

**Response (200 OK):**
```json
{
  "success": true,
  "tasks": [
    {
      "id": "task-uuid-123",
      "container_number": "ABCD1234567",
      "client_name": "ACME Corp",
      "ship_name": "MV Enterprise",
      "status": "pending",
      "worker": {
        "id": "worker-uuid",
        "username": "john_worker"
      },
      "form_type": "desconsolidado",
      "form_name": "Formulario de Desconsolidado",
      "created_at": "2025-10-21T10:00:00+00:00",
      "started_at": null,
      "completed_at": null,
      "is_synced": true
    }
  ],
  "total": 15,
  "offset": 0,
  "limit": 20,
  "user_role": "worker"
}
```

---

### `GET /tasks/<task_id>`
Get detailed information about a specific task.

**Access Control:**
- **Workers:** Can only view own tasks
- **Planners/Admins:** Can view any task

**Response (200 OK):**
```json
{
  "success": true,
  "task": {
    "id": "task-uuid-123",
    "status": "in_progress",
    "container": {
      "number": "ABCD1234567",
      "client_name": "ACME Corp",
      "ship_name": "MV Enterprise",
      "seal_number": "SEAL123",
      "iso_code": "40HC",
      "weight_kg": 15000.5
    },
    "form": {
      "id": "form-uuid",
      "name": "Desconsolidado Form",
      "type": "desconsolidado",
      "questions": [
        {
          "id": "q-uuid-1",
          "text": "¿Cuál es el peso total?",
          "type": "number",
          "is_required": true,
          "order": 1,
          "options": {}
        }
      ]
    },
    "responses": {
      "q-uuid-1": "15000"
    },
    "photos": [
      {
        "question_id": "photo-q-uuid",
        "path": "/uploads/photo123.jpg",
        "timestamp": "2025-10-21T12:30:00+00:00"
      }
    ],
    "worker": {
      "id": "worker-uuid",
      "username": "john_worker"
    },
    "timestamps": {
      "created_at": "2025-10-21T10:00:00+00:00",
      "started_at": "2025-10-21T10:30:00+00:00",
      "completed_at": null,
      "synced_at": "2025-10-21T12:45:00+00:00"
    },
    "is_synced": true
  }
}
```

---

### `PUT|PATCH /tasks/<task_id>/update`
Update a task's data (save form progress or change status).

**Request (JSON):**
```json
{
  "status": "in_progress",
  "responses": {
    "q-uuid-1": "15000",
    "q-uuid-2": "good condition"
  },
  "photos": [
    {
      "question_id": "photo-q-uuid",
      "path": "/uploads/photo456.jpg",
      "timestamp": "2025-10-21T13:00:00+00:00"
    }
  ],
  "mark_synced": true
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Task updated successfully",
  "task": {
    "id": "task-uuid-123",
    "status": "in_progress",
    "updated_at": "2025-10-21T13:05:00+00:00",
    "is_synced": true
  }
}
```

**Status Transitions:**
- `pending` → `in_progress` (automatically sets `started_at`)
- `in_progress` → `completed` (automatically sets `completed_at`)
- `completed` → `reviewed` (automatically sets `reviewed_at`)

---

### `GET /tasks/sync/status`
Get sync status for offline-first PWA.

**Query Parameters:**
- `last_sync` (optional): ISO timestamp of last successful sync

**Example:** `GET /tasks/sync/status?last_sync=2025-10-21T12:00:00Z`

**Response (200 OK):**
```json
{
  "success": true,
  "server_time": "2025-10-21T13:00:00+00:00",
  "needs_sync": {
    "tasks_updated": [
      {
        "id": "task-uuid-1",
        "updated_at": "2025-10-21T12:30:00+00:00",
        "status": "in_progress"
      }
    ],
    "tasks_assigned": [
      {
        "id": "task-uuid-3",
        "assigned_at": "2025-10-21T12:00:00+00:00"
      }
    ],
    "tasks_removed": []
  },
  "sync_conflicts": []
}
```

---

## Worker UI Endpoints

**Access:** Login required (any role).

### `GET /worker/` or `/worker/index`
Worker dashboard showing task statistics.

**Supports both HTML and JSON responses.**

**Response (200 OK) - JSON:**
```json
{
  "success": true,
  "user": {
    "id": "worker-uuid",
    "username": "john_worker",
    "role": "worker",
    "email": "john@example.com"
  },
  "dashboard": {
    "pending_tasks": 5,
    "in_progress_tasks": 2,
    "completed_today": 3,
    "total_assigned": 10
  }
}
```

**HTML Response:**
Renders `worker/index.html` template with dashboard statistics.

---

### `GET /worker/profile`
Worker profile page (HTML only).

---

### `GET /worker/help`
Help and documentation page (HTML only).

---

## Role-Based Access Control

### Authentication Required
All endpoints require authentication except:
- `GET /auth/login`
- `POST /auth/login`

### Role Restrictions

| Endpoint Pattern | Admin | Worker | Planner | Client |
|------------------|-------|--------|---------|--------|
| `/auth/*` | ✅ | ✅ | ✅ | ✅ |
| `/admin/*` | ✅ | ❌ | ❌ | ❌ |
| `/tasks/*` | ✅ | ✅ (own) | ✅ | ❌ |
| `/worker/*` | ✅ | ✅ | ✅ | ✅ |

**Notes:**
- Workers can only view/update their own tasks
- Planners can view/update all tasks
- Admins have full access to everything
- Clients are blocked from task operations

---

## Error Responses

### 400 Bad Request
Invalid request data or validation error.

```json
{
  "success": false,
  "error": "Username is required."
}
```

### 401 Unauthorized
Authentication required or invalid credentials.

```json
{
  "success": false,
  "error": "Authentication required."
}
```

### 403 Forbidden
Insufficient permissions.

```json
{
  "success": false,
  "error": "Admin privileges required."
}
```

### 404 Not Found
Resource not found.

```json
{
  "success": false,
  "error": "Task not found."
}
```

### 500 Internal Server Error
Server-side error.

```json
{
  "success": false,
  "error": "Database error: ..."
}
```

---

## Development Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export FLASK_APP=pytarjas
export FLASK_ENV=development

# Initialize database
flask db init
flask db migrate
flask db upgrade

# Create admin user
python scripts/create_admin.py

# Run development server
flask run
```

---

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=pytarjas

# Run specific test file
pytest tests/test_user_models.py
```

---

## License

[Your License Here]

---

## Contact

[Your Contact Information]