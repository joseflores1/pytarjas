# Pytarjas PWA

A robust Progressive Web App (PWA) designed for managing consolidation and deconsolidation tarja forms in field operations.

## Description

Pytarjas is a full-stack application that provides a seamless interface for field workers, planners, and administrators to manage logistics tasks. It features a dual-response system (HTML and JSON), allowing it to serve both as a traditional web application and a modern API backend for a PWA. The application supports offline-first capabilities, role-based access control (RBAC), and real-time task synchronization.

## Motivation

Field operations in logistics often occur in environments with intermittent or no internet connectivity. Pytarjas was developed to solve this by:
- **Ensuring Continuity:** Providing offline-first capabilities so workers can continue their tasks regardless of network status.
- **Streamlining Workflow:** Automating the transition from pending to completed tasks with real-time sync when connectivity is restored.
- **Improving Accuracy:** Replacing manual paper-based tarja forms with digital versions that include validation and photo documentation.
- **Enhancing Visibility:** Giving planners and admins real-time insights into field operations and worker performance.

## Quick Start

### Prerequisites
- Python 3.10+
- `pip` or `uv` package manager

### Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd pytarjas_hgt
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set environment variables:**
   ```bash
   export FLASK_APP=main.py
   export FLASK_ENV=development
   ```

4. **Initialize the database:**
   ```bash
   flask db upgrade
   ```

5. **Run the development server:**
   ```bash
   python main.py
   ```
   The application will be available at `http://localhost:5000`.

## Usage

### User Roles
- **Admin:** Manage users, view system-wide statistics, and perform all operations.
- **Planner:** Create and assign tasks, monitor all worker progress.
- **Worker:** Access the dashboard to view assigned tasks, fill out tarja forms, and upload documentation.
- **Client:** View reports and status updates for their specific containers (Read-only).

### Key Features
- **Dashboard:** Role-specific views with real-time statistics.
- **Task Management:** CRUD operations for logistics tasks with support for ad-hoc fields.
- **Form Versioning:** Manage multiple versions of tarja forms with activation control.
- **Planning Templates:** Define batch metadata fields for recurring logistics operations.
- **PDF Generation:** Generate professional tarja reports in PDF format.
- **Offline Sync:** Built-in support for offline progress saving and synchronization.

## API & UI Endpoints

Pytarjas is organized into several blueprints, each serving specific roles or data artifacts. Most endpoints support both HTML (for UI) and JSON (for API) responses.

### Authentication (`/auth`)
- `GET /auth/login`: Display login form.
- `POST /auth/login`: Authenticate a user and create a session.
- `GET|POST /auth/logout`: End the current user session.
- `GET /auth/session`: Check current authentication status (API friendly).

### Admin Dashboard (`/admin`)
- `GET /admin/`: Main dashboard for administrators showing user and form statistics.

### User Management (`/users`)
- `GET /users/`: List all users (supports `role` filtering).
- `GET /users/create`: Display user creation form.
- `POST /users/create`: Create a new user.
- `GET /users/<user_id>/edit`: Display user edit form.
- `POST|PATCH /users/<user_id>/edit`: Update an existing user.
- `POST|DELETE /users/<user_id>/delete`: Delete a user from the system.

### Tasks Management (`/tasks`)
- `GET /tasks/`: List all tasks (supports filtering by `status`, `worker_id`, `container_number`, etc.).
- `GET /tasks/create`: Display task creation form.
- `POST /tasks/create`: Create a new task.
- `GET /tasks/<task_id>`: Get detailed information about a specific task.
- `PUT|PATCH /tasks/<task_id>/update`: Update task data (responses, status, photos).
- `POST /tasks/<task_id>/upload_file`: Upload a file for a specific task question.
- `GET /tasks/<task_id>/pdf`: Generate and download the Tarja PDF report.

### Forms & Templates (`/forms`)
- `GET /forms/`: List all form templates and their versions.
- `GET /forms/create`: Display form creation UI.
- `POST /forms/create`: Create a new form template (with versioning).
- `GET /forms/<form_id>`: View form details and its questions.
- `GET /forms/<form_id>/edit`: Edit an existing form version.
- `POST /forms/<form_id>/activate`: Set a specific form version as active.
- `POST|DELETE /forms/<form_id>/delete`: Remove a form version.

### Plannings (`/plannings`)
- `GET /plannings/`: List all work plannings.
- `GET /plannings/create`: Display planning creation form.
- `POST /plannings/create`: Create a new planning (batch of tasks).
- `GET /plannings/<planning_id>`: View planning details and assigned tasks.
- `GET /plannings/templates`: List metadata templates for plannings.
- `GET /plannings/templates/create`: Create a new metadata template.
- `POST /plannings/templates/delete/<template_id>`: Delete a metadata template.

### Worker Interface (`/worker`)
- `GET /worker/`: Worker dashboard with task statistics.
- `GET /worker/tasks`: List of tasks assigned to the current worker.
- `GET /worker/profile`: View current worker profile information.

### Planner & Client Interfaces
- `GET /planner/`: Planner-specific landing page.
- `GET /client/`: Client-specific landing page (currently redirects to worker view).

## Architecture

Pytarjas is built using:
- **Backend:** Flask (Python)
- **Database:** PostgreSQL/SQLite with SQLAlchemy ORM
- **Migrations:** Alembic (Flask-Migrate)
- **Frontend:** HTML5, CSS3 (Vanilla), JavaScript (Vanilla)
- **Services:** Specialized services for PDF generation and File Storage.
