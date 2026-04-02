# 🏛️ KimConnect - Sol Plaatje Municipal Service Portal

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/Django-6.0-green.svg" alt="Django">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License">
  <img src="https://img.shields.io/badge/South%20Africa-Northern%20Cape-red.svg" alt="Location">
</p>

> **KimConnect** is a world-class municipal service platform for the Sol Plaatje Municipality in Kimberley, Northern Cape, South Africa. It empowers citizens to report and track municipal issues while providing staff with powerful management tools.

---

## 🌟 Features

### For Citizens
- 📝 **Easy Issue Reporting** - Report water leaks, potholes, electricity issues, and more
- 🔍 **Real-time Tracking** - Track your reported issues with unique codes
- 💬 **AI Chatbot** - 24/7 assistance with voice input support
- 🌐 **Multi-language** - English, Afrikaans, isiXhosa, isiZulu
- 📱 **PWA Support** - Install as a mobile app
- 📵 **Offline Mode** - Report issues even without internet
- 🔔 **Push Notifications** - Get status updates instantly
- 📸 **Photo Upload** - AI-powered image analysis
- 🗺️ **Interactive Maps** - GIS heatmap visualization

### For Staff
- 📊 **Analytics Dashboard** - Real-time statistics and insights
- 👥 **Issue Management** - Assign, escalate, and resolve issues
- 📈 **SLA Tracking** - Automatic deadline monitoring
- 🎯 **Performance Metrics** - Track team productivity
- 🏆 **Gamification** - Points, badges, and leaderboards

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- pip (Python package manager)

### Installation (Local)

1. **Clone the repository**
```
git clone https://github.com/yourusername/kimconnect.git
cd kimconnect
```

2. **Virtual environment**
```
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\\Scripts\\activate    # Windows
```

3. **Dependencies**
```
pip install -r requirements.txt
```

4. **Migrations**
```
python manage.py migrate
```

5. **Superuser**
```
python manage.py createsuperuser
```

6. **Runserver**
```
python manage.py runserver
```
**Local:** http://127.0.0.1:8000/

### 🚀 Production Deployment

#### Render.com (Recommended - Free Tier)
1. **Fork/Push to GitHub** this repo
2. **render.com** → New Web Service → Connect GitHub repo
3. **Settings:**
   ```
   Runtime: Python 3
   Build: pip install -r requirements.txt
   Start: gunicorn municipal_service.wsgi
   ```
4. **Environment Vars:**
   ```
   PYTHON_VERSION=3.12.7
   SECRET_KEY=your-secret-key
   DEBUG=False
   DATABASE_URL=postgres://... (Render Postgres)
   ```
5. **Deploy** → Live URL: https://your-app.onrender.com

#### Netlify (Static Frontend + API)
1. **Static export:** `python manage.py collectstatic`
2. **Netlify deploy** static/ folder
3. **Backend:** Render/Heroku for Django API

#### GitHub Codespaces
```
gh codespace create --repo yourusername/kimconnect --machine linux
```

**Deployed live:** [Render](https://kimconnect.onrender.com) | [Netlify Static](https://kimconnect.netlify.app)



---

## 📁 Project Structure

```
kimconnect/
├── municipal_service/       # Django project settings
│   ├── settings.py          # Configuration
│   ├── urls.py             # Root URL routing
│   └── wsgi.py             # WSGI application
├── reporting/               # Citizen reporting app
│   ├── models.py           # Issue, Vote, Image models
│   ├── views.py            # Report, track views
│   ├── forms.py            # Report forms
│   ├── ai_chatbot.py       # AI chatbot integration
│   ├── gamification.py      # Points & badges
│   └── sms_notifications.py # SMS integration
├── tracking/                # Staff tracking app
│   ├── models.py           # StatusUpdate, SLA models
│   ├── views.py            # Dashboard, analytics
│   └── admin.py            # Admin configuration
├── templates/               # HTML templates
│   ├── base.html           # Base template
│   ├── home.html           # Home page
│   ├── components/         # Reusable components
│   └── tracking/           # Tracking templates
├── static/                  # Static files
│   ├── js/                # JavaScript files
│   ├── icons/             # PWA icons
│   └── manifest.json       # PWA manifest
└── manage.py               # Django management
```

---

## 🔧 Configuration

### Environment Variables (Optional)

Create a `.env` file in the project root:

```env
# Django
SECRET_KEY=your-secret-key-here
DEBUG=True

# OpenAI (Optional - for AI chatbot)
OPENAI_API_KEY=sk-...

# Twilio (Optional - for SMS)
TWILIO_ACCOUNT_SID=your-sid
TWILIO_AUTH_TOKEN=your-token
TWILIO_FROM_NUMBER=+1234567890

# Africa's Talking (Optional)
AFRICA_TALKING_API_KEY=your-api-key
AFRICA_TALKING_USERNAME=sandbox
```

### Database

The project uses SQLite by default. For production:

```python
# municipal_service/settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'kimconnect',
        'USER': 'postgres',
        'PASSWORD': 'your-password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

---

## 🎨 Screenshots

| Feature | Description |
|---------|-------------|
| Home Page | Hero section, issue statistics, quick actions |
| Report Form | Multi-step form with photo upload |
| Tracking | Real-time status timeline |
| Dashboard | Staff analytics and management |
| AI Chatbot | 24/7 assistance |
| Gamification | Points, badges, leaderboards |

---

## 🌐 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/stats/` | GET | Get issue statistics |
| `/api/issues/geo/` | GET | Get issues with coordinates |
| `/api/leaderboard/` | GET | Get gamification leaderboard |
| `/api/chatbot/` | POST | AI chatbot endpoint |

---

## 🤖 Advanced Features

### AI Integration
```python
# Use OpenAI GPT-4
AI_CHATBOT_PROVIDER = 'openai'
OPENAI_API_KEY = 'your-key'

# Use Claude
AI_CHATBOT_PROVIDER = 'claude'
ANTHROPIC_API_KEY = 'your-key'
```

### SMS Notifications
```python
# Twilio
SMS_PROVIDER = 'twilio'

# Africa's Talking
SMS_PROVIDER = 'africa_talking'
```

### PWA Features
The app works offline with:
- Service Worker caching
- IndexedDB for pending reports
- Background sync when online

---

## 📊 Comparison with FixMyStreet

| Feature | KimConnect | FixMyStreet |
|---------|------------|-------------|
| AI Chatbot | ✅ | ❌ |
| Voice Input | ✅ | ❌ |
| Offline Support | ✅ | ❌ |
| PWA | ✅ | Partial |
| Multi-language | ✅ (4 SA) | ❌ |
| Gamification | ✅ | ❌ |
| Budget Transparency | ✅ | ❌ |
| GIS Heatmaps | ✅ | ❌ |
| Push Notifications | ✅ | ❌ |
| Volunteer System | ✅ | ❌ |

---

## 🧪 Testing

```bash
# Run all tests
python manage.py test

# Run with coverage
python -m coverage run manage.py test
python -m coverage report
```

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 👥 Contributors

- Developed for Sol Plaatje Municipality
- Designed following HCI principles for South African citizens
- Optimized for mobile-first experience

---

## 🇿🇦 Acknowledgments

- Sol Plaatje Municipality, Kimberley
- Northern Cape Provincial Government
- OpenStreetMap Contributors
- Django Community

---

<p align="center">
  <strong>Built with ❤️ for Kimberley, South Africa</strong>
</p>
