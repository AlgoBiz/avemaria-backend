# Avemaria Career Guidance Center — Backend API

Django REST Framework backend for **Avemaria Career Guidance Center Ltd. (UK)**.  
Provides RESTful APIs supporting both the public-facing educational web portal (`https://avemaria-frontend.vercel.app`) and the comprehensive administrator management dashboard (`/admin`).

---

## 🛠️ Tech Stack & Key Libraries

| Technology | Purpose |
| :--- | :--- |
| **Django (3.2+)** | Core high-level web framework, ORM, migrations, and admin site |
| **Django REST Framework (3.15+)** | REST API engine, serializers, viewsets, and permissions |
| **SimpleJWT (5.2+)** | JSON Web Token (JWT) authentication for admin and student portals |
| **drf-spectacular (0.24+)** | OpenAPI 3.0 schema generation with interactive Swagger UI & ReDoc |
| **django-cors-headers** | Cross-Origin Resource Sharing (CORS) middleware for frontend clients |
| **django-filter** | Dynamic queryset filtering across courses, blogs, resources, and leads |
| **Pillow** | Image processing and validation for faculty portraits, course banners, and gallery photos |
| **ReportLab** | Server-side PDF generation for student payment receipts and tax invoices |
| **python-decouple** | Environment variable and configuration management (`.env`) |
| **psycopg2-binary** | PostgreSQL database adapter for production environments |
| **WhiteNoise** | Efficient static asset serving in production environments |

---

## 📁 Project Architecture

```
avemaria-backend/
├── core/                           # Django project configuration & root routing
│   ├── __init__.py
│   ├── asgi.py                     # ASGI entrypoint for async/websockets
│   ├── models.py                   # BaseModel (audit timestamps, soft-delete)
│   ├── settings.py                 # Project configuration & third-party settings
│   ├── urls.py                     # Root URL routing & OpenAPI schema mounts
│   └── wsgi.py                     # WSGI entrypoint for production servers
├── apps/                           # Domain applications (Models, business logic)
│   ├── accounts/                   # Custom User model & admin authentication
│   ├── categories/                 # Course & resource categorization
│   ├── courses/                    # Comprehensive course curriculum & syllabus
│   ├── faculty/                    # Faculty members, qualifications & mentors
│   ├── resources/                  # Paid study materials, PDFs & purchase tracking
│   ├── testimonials/               # Student reviews, ratings & feedback
│   ├── gallery/                    # Campus facilities & lab training photo albums
│   ├── enquiries/                  # Admission leads, consultation requests & CSV export
│   ├── blogs/                      # Educational articles & rich-content blocks
│   ├── students/                   # Learner profiles, document repository & tracking
│   └── portal_settings/            # Institutional metadata, branding & contact details
├── api/                            # Versioned REST API layer
│   └── v1/                         # API v1 serializers, viewsets, and routing
│       ├── auth/                   # Authentication (JWT, Admin, Student, OTP reset)
│       ├── dashboard/              # Admin overview metrics & summary statistics
│       ├── courses/                # Course catalog & curriculum endpoints
│       ├── categories/             # Course categories endpoints
│       ├── faculty/                # Faculty directory & mentor profiles
│       ├── resources/              # Study materials catalog & purchase validation
│       ├── testimonials/           # Student success testimonials
│       ├── gallery/                # Photo albums & categorization
│       ├── enquiries/              # Lead capture forms & administrative lead pipeline
│       ├── blogs/                  # Articles, tags, and category endpoints
│       ├── students/               # Student management & verification
│       └── portal_settings/        # Institutional details & platform configuration
├── templates/                      # HTML transactional email templates
│   └── emails/
│       ├── admin_otp_email.html                # Admin OTP password reset
│       ├── admin_password_reset.html           # Admin password recovery link
│       ├── student_otp_email.html              # Student OTP verification
│       └── student_purchase_receipt_email.html # Resource purchase receipt & invoice
├── .env.example                    # Environment variable template
├── .gitignore                      # Git exclusion rules
├── requirements.txt                # Python dependencies
├── manage.py                       # Django command-line utility
└── README.md                       # Project documentation
```

---

## 🚀 Getting Started

### 1. Prerequisites
- Python **3.9+** or **3.10+**
- `pip` (Python package manager)
- `virtualenv` or Python `venv` module

### 2. Clone and Setup Environment
```bash
# Clone the repository
git clone <repository-url>
cd avemaria-backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows PowerShell:
.\venv\Scripts\Activate.ps1
# Windows Command Prompt (CMD):
.\venv\Scripts\activate.bat
# macOS / Linux:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy the sample environment file to `.env`:
```bash
# Windows PowerShell / CMD:
copy .env.example .env

# macOS / Linux:
cp .env.example .env
```
Update `.env` with your local settings (see [Environment Variables](#-environment-variables) below).

### 5. Run Database Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### 6. Create Superuser (Admin Account)
```bash
python manage.py createsuperuser
```

### 7. Run Local Development Server
```bash
python manage.py runserver
```
The server will start at `http://127.0.0.1:8000/`.

---

## ⚙️ Environment Variables

Configure the following variables in your `.env` file:

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `DEBUG` | `True` | Enable/disable debug mode (`True` for local, `False` for production) |
| `SECRET_KEY` | `django-insecure-...` | Django cryptographic signing secret key |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1,*` | Comma-separated allowed hostnames/IPs |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:3000,...` | Comma-separated allowed CORS client origins |
| `EMAIL_BACKEND` | `django.core.mail.backends.smtp.EmailBackend` | Email backend (or `console.EmailBackend` for testing) |
| `EMAIL_HOST` | `smtp.gmail.com` | SMTP host address |
| `EMAIL_PORT` | `587` | SMTP port number |
| `EMAIL_USE_TLS` | `True` | Enable TLS security for email dispatch |
| `EMAIL_HOST_USER` | `""` | SMTP sender username / email |
| `EMAIL_HOST_PASSWORD` | `""` | SMTP application password |
| `DEFAULT_FROM_EMAIL` | Same as `EMAIL_HOST_USER` | Default "From" address for outgoing system emails |
| `FRONTEND_URL` | `https://avemaria-frontend.vercel.app` | Base URL of frontend application (for reset links) |

---

## 📖 API Documentation & Schema

Interactive documentation is built into the API via `drf-spectacular`:

- **Swagger UI:** [http://127.0.0.1:8000/api/docs/](http://127.0.0.1:8000/api/docs/)
- **ReDoc:** [http://127.0.0.1:8000/api/redoc/](http://127.0.0.1:8000/api/redoc/)
- **OpenAPI 3.0 Schema (YAML/JSON):** [http://127.0.0.1:8000/api/schema/](http://127.0.0.1:8000/api/schema/)

---

## 📡 API Endpoints Overview

All primary API routes are versioned under `/api/v1/`:

### 1. Authentication & Accounts (`/api/v1/auth/`)
- **JWT Token Management:**
  - `POST /api/v1/auth/token/` — Obtain JWT access & refresh tokens
  - `POST /api/v1/auth/token/refresh/` — Refresh access token
  - `POST /api/v1/auth/token/verify/` — Validate token integrity
- **Administrator Auth & Security:**
  - `POST /api/v1/auth/admin/login/` — Admin login
  - `GET /api/v1/auth/profile/` — Admin profile details
  - `POST /api/v1/auth/change-password/` — Change admin password
  - `POST /api/v1/auth/password-reset/` — Request password reset link via email
  - `POST /api/v1/auth/otp/request/` — Request email OTP for password reset
  - `POST /api/v1/auth/otp/verify/` — Verify email OTP
  - `POST /api/v1/auth/otp/confirm/` — Reset password using OTP
- **Student Authentication & Portal:**
  - `POST /api/v1/auth/student/register/` — Register new student account
  - `POST /api/v1/auth/student/login/` — Student login
  - `GET|PUT|PATCH /api/v1/auth/student/profile/` — View and edit student profile
  - `POST /api/v1/auth/student/change-password/` — Update student password
  - `POST /api/v1/auth/student/logout/` — Student logout
  - `POST /api/v1/auth/student/otp/request/` — Student forgot password OTP request
  - `POST /api/v1/auth/student/otp/verify/` — Verify student OTP
  - `POST /api/v1/auth/student/otp/confirm/` — Set new password with verified OTP
  - `GET|POST /api/v1/auth/student/documents/` — Upload & view KYC/academic documents
  - `GET|POST /api/v1/auth/student/courses/` — List enrolled courses / self-enroll
  - `GET /api/v1/auth/student/resources/` — List purchased study materials
  - `POST /api/v1/auth/student/resources/purchase/` — Purchase study resources
  - `GET /api/v1/auth/student/receipts/` — Access payment receipts & PDF invoices

### 2. Courses & Categories (`/api/v1/courses/`)
- `GET /api/v1/courses/` — List published courses (filterable by category, search)
- `POST /api/v1/courses/` — Create new course (Admin only)
- `GET|PUT|PATCH|DELETE /api/v1/courses/<id>/` — Course details and management
- `GET|POST /api/v1/courses/categories/` — Course categories listing & creation

### 3. Faculty & Mentors (`/api/v1/faculty/` or `/api/v1/faculties/`)
- `GET /api/v1/faculty/` — Public listing of qualified faculty and mentors
- `POST /api/v1/faculty/` — Add faculty member (Admin only)
- `GET|PUT|PATCH|DELETE /api/v1/faculty/<id>/` — View/update faculty profile

### 4. Study Resources (`/api/v1/resources/`)
- `GET /api/v1/resources/` — Browse downloadable paid resources & study guides
- `POST /api/v1/resources/` — Create resource (Admin only)
- `POST /api/v1/resources/categories/create/` — Create resource category

### 5. Campus Gallery (`/api/v1/gallery/`)
- `GET /api/v1/gallery/` — View campus, lab, and event photo albums
- `GET /api/v1/gallery/categories/` — View gallery categories

### 6. Testimonials (`/api/v1/testimonials/`)
- `GET /api/v1/testimonials/` — Public list of student testimonials and reviews
- `POST|PUT|DELETE /api/v1/testimonials/` — Manage student testimonials (Admin)

### 7. Admissions & Enquiries (`/api/v1/enquiries/`)
- `POST /api/v1/enquiries/` — Submit lead / contact inquiry form (Public)
- `GET /api/v1/enquiries/` — Manage admissions inquiries & pipeline (Admin)
- `GET /api/v1/enquiries/export/` — Export inquiry leads as CSV (Admin)

### 8. Blog & Articles (`/api/v1/blogs/` or `/api/v1/blog/`)
- `GET /api/v1/blogs/` — Published blog articles and guides
- `GET /api/v1/blogs/categories/` — Blog topic categories
- `POST|PUT|PATCH|DELETE /api/v1/blogs/` — Content management (Admin)

### 9. Student Management (`/api/v1/students/`)
- `GET /api/v1/students/` — Comprehensive learner directory (Admin)
- `GET|PUT|PATCH|DELETE /api/v1/students/<id>/` — Student profile and enrollment records

### 10. Dashboard & System Settings
- `GET /api/v1/dashboard/` (or `overview/`) — Aggregated statistics & operational counts
- `GET|PUT|PATCH /api/v1/settings/` — Portal contact details, branding, and platform settings

---

## 🔒 Authentication

Requests to protected endpoints require a JWT Bearer token in the `Authorization` header:

```http
Authorization: Bearer <your-access-token>
```

Tokens can be acquired via `/api/v1/auth/token/`, `/api/v1/auth/admin/login/`, or `/api/v1/auth/student/login/`.

---

## 📦 Production Deployment Notes

1. **Set `DEBUG=False`** in production `.env`.
2. **Collect Static Files:**
   ```bash
   python manage.py collectstatic --noinput
   ```
3. **Database Configuration:**
   Use PostgreSQL in production by setting connection parameters or `DATABASE_URL` with `psycopg2-binary`.
4. **WSGI / ASGI Application Server:**
   Deploy using Gunicorn or Uvicorn:
   ```bash
   # Gunicorn (WSGI):
   gunicorn core.wsgi:application --bind 0.0.0.0:8000 --workers 4

   # Uvicorn (ASGI):
   uvicorn core.asgi:application --host 0.0.0.0 --port 8000
   ```
