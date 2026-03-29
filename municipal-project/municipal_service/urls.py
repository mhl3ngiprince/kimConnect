from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from reporting.views import home_view, register_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home_view, name='home'),
    
    # Authentication
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
    path('register/', register_view, name='register'),
    
    # App URLs
    path('reporting/', include('reporting.urls')),
    path('tracking/', include('tracking.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
