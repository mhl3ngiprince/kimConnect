from django.urls import path
from . import views

app_name = 'reporting'

urlpatterns = [
    # Issue Reporting
    path('report/', views.report_issue, name='report_issue'),
    path('report/quick/', views.quick_report, name='quick_report'),
    
    # Issue Listing & Search
    path('issues/', views.issue_list, name='issue_list'),
    path('search/', views.issue_list, name='issue_search'),
    
    # Public Issue Tracking
    path('track/', views.track_issue, name='track_issue'),
    path('track/<str:tracking_code>/', views.issue_detail_public, name='issue_public'),
    
    # Comments & Voting
    path('issue/<int:pk>/comment/', views.add_comment, name='add_comment'),
    path('issue/<int:pk>/vote/', views.vote_issue, name='vote_issue'),
    
    # API Endpoints
    path('api/report/', views.api_report_issue, name='api_report'),
    path('api/issue/<str:tracking_code>/', views.api_get_issue, name='api_get_issue'),
]
