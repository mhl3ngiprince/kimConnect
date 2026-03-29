from django.contrib import admin
from .models import Issue, IssueImage, IssueComment, IssueVote, IssueCategory, Department, NotificationLog


@admin.register(Issue)
class IssueAdmin(admin.ModelAdmin):
    list_display = ['tracking_code', 'title', 'issue_type', 'priority', 'status', 'assigned_department', 'created_at']
    list_filter = ['status', 'priority', 'issue_type', 'created_at', 'assigned_department']
    search_fields = ['tracking_code', 'title', 'location', 'description', 'reporter_email']
    readonly_fields = ['tracking_code', 'created_at', 'updated_at', 'submitted_at', 'sla_due_at']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    fieldsets = (
        ('Issue Information', {
            'fields': ('tracking_code', 'title', 'issue_type', 'category', 'description')
        }),
        ('Location', {
            'fields': ('location', 'latitude', 'longitude', 'location_accuracy', 'ward', 'suburb')
        }),
        ('Status & Priority', {
            'fields': ('status', 'priority', 'suggested_priority', 'assigned_department', 'assigned_staff')
        }),
        ('Reporter', {
            'fields': ('reporter_name', 'reporter_email', 'reporter_phone', 'is_anonymous', 'notification_preferences')
        }),
        ('SLA', {
            'fields': ('sla_due_at', 'sla_breached', 'estimated_resolution')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'submitted_at', 'acknowledged_at', 'in_progress_at', 'resolved_at', 'closed_at')
        }),
        ('Community', {
            'fields': ('verification_status', 'upvotes', 'downvotes', 'reports_count')
        }),
    )


@admin.register(IssueCategory)
class IssueCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'department', 'estimated_response_time', 'is_active']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'email', 'is_active']
    list_filter = ['is_active']


@admin.register(IssueComment)
class IssueCommentAdmin(admin.ModelAdmin):
    list_display = ['issue', 'author_name', 'is_official', 'is_anonymous', 'created_at']
    list_filter = ['is_official', 'is_anonymous', 'created_at']
    search_fields = ['author_name', 'author_email', 'content']


@admin.register(IssueVote)
class IssueVoteAdmin(admin.ModelAdmin):
    list_display = ['issue', 'voter_ip', 'vote_type', 'created_at']
    list_filter = ['vote_type', 'created_at']


@admin.register(IssueImage)
class IssueImageAdmin(admin.ModelAdmin):
    list_display = ['id', 'uploaded_at', 'is_primary', 'uploaded_by']
    list_filter = ['is_primary', 'uploaded_at']


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ['issue', 'notification_type', 'channel', 'recipient', 'sent_at', 'delivered']
    list_filter = ['notification_type', 'channel', 'delivered']
    search_fields = ['recipient', 'issue__tracking_code']
    readonly_fields = ['sent_at']
