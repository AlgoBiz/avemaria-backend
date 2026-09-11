# Avemaria Career Guidance Center — Backend API

Django REST Framework backend for Avemaria Career Guidance Center Ltd. (UK).
Provides REST APIs for both the public-facing educational portal (`avemaria-frontend.vercel.app`) and the comprehensive administrator dashboard (`/admin`).

---

## 🛠️ Tech Stack
- **Framework:** Django 3.2+ & Django REST Framework (DRF)
- **Authentication:** JWT (JSON Web Tokens) via `djangorestframework-simplejwt`
- **Documentation:** Interactive OpenAPI / Swagger (`drf-spectacular`)
- **Database:** SQLite (local development) / PostgreSQL / MySQL ready
- **Media / Storage:** Django Media storage with support for course banners, PDF packs, avatars, and gallery images
- **CORS:** `django-cors-headers`

---

## 📁 Architecture

```
Avemaria/
├── core/                       # Django project root settings & routing
│   ├── __init__.py
│   ├── asgi.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── apps/                       # Domain apps (Models, business logic)
│   ├── accounts/               # Custom user & admin profile
│   ├── categories/             # Course categories
│   ├── courses/                # Comprehensive programmes & curriculum
│   ├── resources/              # Paid study resources & downloadable PDFs
│   ├── testimonials/           # Student success reviews & ratings
│   ├── gallery/                # Campus & lab training photos
│   ├── enquiries/              # Candidate admissions leads & CSV export
│   ├── blogs/                  # Educational blogs & dynamic block builder
│   ├── students/               # Registered learners directory
│   └── portal_settings/        # Institutional details & dashboard metrics
├── api/
│   └── v1/                     # Versioned REST API Endpoints
│       ├── auth/               # Login, refresh token, password change
│       ├── dashboard/          # Summary metrics & quick shortcuts
│       ├── categories/         # Categories public & admin viewsets
│       ├── courses/            # Course catalogue & programme builder
│       ├── resources/          # Study packs & PDF file management
│       ├── testimonials/       # Reviews & ratings
│       ├── gallery/            # Campus photo gallery
│       ├── enquiries/          # Lead collection & CSV export
│       ├── blogs/              # Blogs & content blocks
│       ├── students/           # Student directory & contact triggers
│       └── portal_settings/    # Brand configuration
├── .env                        # Local environment variables
├── .env.example                # Example environment template
├── .gitignore                  # Git exclusions
├── requirements.txt            # Python dependencies
├── manage.py                   # Django CLI tool
└── README.md                   # Documentation
```

---

## 🚀 Getting Started

### 1. Activate Virtual Environment
```bash
python -m venv venv
# On Windows PowerShell:
.\venv\Scripts\Activate.ps1
# On Windows CMD:
.\venv\Scripts\activate.bat
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### 4. Create Superuser (Admin)
```bash
python manage.py createsuperuser
```

### 5. Start Development Server
```bash
python manage.py runserver
```

---

## 📖 API Documentation
Once the server is running, explore interactive API documentation:
- **Swagger UI:** [http://127.0.0.1:8000/api/docs/](http://127.0.0.1:8000/api/docs/)
- **ReDoc:** [http://127.0.0.1:8000/api/redoc/](http://127.0.0.1:8000/api/redoc/)
- **OpenAPI Schema:** [http://127.0.0.1:8000/api/schema/](http://127.0.0.1:8000/api/schema/)
