# Synca

> Syncing up with the perfect place.
```


## Overview

Synca is a Django-powered platform that helps students discover, evaluate, and book Paying Guest (PG) and hostel accommodations while giving owners a modern dashboard to manage inventory at the room and bed level. The system tracks online and offline bookings, keeps availability in sync, and provides self-service tools for both owners and tenants.

Key highlights:
- Granular room/bed model with automated occupancy tracking.
- Owner workflow for publishing properties, adding rooms/beds, and recording offline bookings.
- Student portal with profile management, booking history, and self-serve date updates/cancellations.
- Responsive UI built with Bootstrap 5 and custom styling.

## Feature Snapshot

### Student Experience
- [x] Account registration/login (Django auth) with student profile enrichment.
- [x] Browse PG listings with detail pages and property imagery.
- [x] Booking history dashboard with status badges (upcoming/active/completed/cancelled).
- [x] Self-service booking management (date updates, cancellations, room/bed context).
- [ ] Advanced search & filtering by rent/amenities.
- [ ] Ratings and reviews on PG listings.
- [ ] Payments integration.

### Owner Experience
- [x] Owner dashboard with property stats and live occupancy metrics.
- [x] Add/update property listings with media uploads, amenities, and lock-in/deposit metadata.
- [x] Room and bed management (add rooms, add beds, toggle availability).
- [x] Record and manage offline/online bookings, including tenant assignment.
- [x] Visual cues for cancelled bookings (greyed cards) and booking status badges.
- [ ] Bulk import/export tools.
- [ ] Automated billing & invoicing.

### Technical Stack
- **Backend:** Python 3.13, Django 5.2
- **Database:** MySQL (InnoDB)
- **Frontend:** HTML5, Bootstrap 5, Vanilla JS
- **Assets:** Django static files + media uploads (images stored under `media/`)

---

## Getting Started

Follow the steps below to run Synca locally.

### 1. Prerequisites
- Python 3.12+ (project tested on 3.13)
- MySQL 8 (or compatible) with a database and user provisioned
- Git, Node.js (optional for frontend tooling)

### 2. Clone & Create a Virtual Environment
```powershell
# Windows PowerShell
cd D:\projects
git clone https://github.com/Shash-135/Synca.git
cd Synca
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies
```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure Environment
Create a `.env` file (or export variables) with your database credentials. Defaults expected by the project:
```
DB_NAME=synca_db
DB_USER=synca_user
DB_PASSWORD=synca123
DB_HOST=127.0.0.1
DB_PORT=3306
DJANGO_SECRET_KEY=replace-me
DJANGO_DEBUG=True
```
Update `synca_project/settings.py` to read from these variables for production hardening if needed.

### 5. Prepare the Database
```sql
CREATE DATABASE synca_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'synca_user'@'%' IDENTIFIED BY 'synca123';
GRANT ALL PRIVILEGES ON synca_db.* TO 'synca_user'@'%';
FLUSH PRIVILEGES;
```

### 6. Apply Migrations & Create a Superuser
```powershell
python manage.py migrate
python manage.py createsuperuser
```

### 7. Media & Static Assets
- Property images uploaded through the owner flow land in `media/pg_images/` (configured via `MEDIA_ROOT`).
- Create the `media` directory if it does not exist: `mkdir media`.
- `MEDIA_URL = /media/` enables Django to serve files in development; in production serve media via Nginx/S3/etc.
- Static assets live under `static/` and are collected with `python manage.py collectstatic` when deploying.

### 8. Run the Development Server
```powershell
python manage.py runserver
```
Visit [http://127.0.0.1:8000/](http://127.0.0.1:8000/) and log in with a student or owner account.

---

## Project Structure
```
Synca/
├─ core/                  # Domain models, services, class-based views, forms, URLs
├─ templates/             # Django templates (layouts, pages, partials)
├─ static/                # CSS, JS, images
├─ media/                 # Uploaded assets (created at runtime)
├─ synca_project/         # Project settings & URL configuration
├─ manage.py
└─ requirements.txt
```

---

## Developer Guide

### Running Checks & Tests
```powershell
python manage.py check
python manage.py test
```
> The automated test suite is currently light; add coverage alongside new features.

### Coding Standards
- Python: follow PEP 8 (consider `black` + `isort`).
- Templates/CSS: keep Bootstrap 5 utility classes, prefer mobile-first layout tweaks.
- JavaScript: vanilla ES6; modularise reusable snippets under `static/js/`.

### Service Layer Overview
The Django app now organises complex orchestration logic into dedicated services under `core/services/`:
- `pg.py` bundles catalog/detail builders for public pages.
- `owner.py` delivers dashboard aggregates, inventory helpers (room/bed creation, booking approvals), and offline booking flows.
- `student.py` centralises booking quotes, profile updates, history grouping, and mutation helpers.

Each class-based view composes these services to keep controllers thin and reuse domain logic across features. When adding new functionality, prefer introducing a service first and then consuming it from the view.

### Useful Commands
- `python manage.py dumpdata core.Booking --indent 2 > backup.json` to snapshot bookings.
- `python manage.py loaddata backup.json` to restore sample data.
- `python manage.py shell_plus` (if you enable `django-extensions`) for interactive debugging.

### Session Policy
- Sessions follow Django's default behavior: users stay signed in until they log out or their cookie naturally expires.
- No automatic logout is triggered on tab switches, reloads, or browser close; adjust `SESSION_COOKIE_AGE` in `settings.py` if you need custom lifetimes.

---

## Roadmap
- [ ] Student-side advanced search & filters
- [ ] Ratings & reviews engine
- [ ] Owner notifications & reminder emails
- [ ] Payment gateway mock integration
- [ ] Automated bed assignment recommendations

Contributions are welcome! Open an issue or submit a PR if you have ideas to improve Synca.
