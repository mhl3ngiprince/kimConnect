from django.urls import path
from . import views

app_name = 'tracking'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    path('stats/', views.dashboard_stats_json, name='dashboard_stats'),
    
    # Issue Management
    path('issue/<int:pk>/', views.issue_detail, name='issue_detail'),
    path('issue/<int:pk>/update/', views.update_status, name='update_status'),
    path('issue/<int:pk>/assign/', views.assign_staff, name='assign_staff'),
    path('issue/<int:pk>/escalate/', views.escalate_issue, name='escalate_issue'),
    
    # Real-time Updates
    path('issue/<int:pk>/timeline/', views.issue_timeline_sse, name='issue_timeline'),
    
    # Analytics
    path('analytics/', views.analytics_view, name='analytics'),
]
