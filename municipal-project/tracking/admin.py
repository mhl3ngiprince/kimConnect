from django.contrib import admin
from .models import StatusUpdate, StaffMember, IssueAssignment, SLATracking, EscalationLog, IssueMetric, EscalationRule, AutomatedAction, NotificationPreference


@admin.register(StatusUpdate)
class StatusUpdateAdmin(admin.ModelAdmin):
    list_display = ['issue', 'new_status', 'updated_by', 'timestamp', 'update_type']
    list_filter = ['new_status', 'update_type', 'timestamp']
    search_fields = ['issue__tracking_code', 'message', 'updated_by']
    readonly_fields = ['timestamp']


@admin.register(StaffMember)
class StaffMemberAdmin(admin.ModelAdmin):
    list_display = ['name', 'department', 'role', 'is_active', 'current_load']
    list_filter = ['department', 'role', 'is_active']
    search_fields = ['name', 'email', 'department']


@admin.register(IssueAssignment)
class IssueAssignmentAdmin(admin.ModelAdmin):
    list_display = ['issue', 'staff', 'assigned_at', 'is_primary', 'is_active']
    list_filter = ['is_primary', 'is_active', 'assigned_at']
    search_fields = ['issue__tracking_code', 'staff__name']


@admin.register(SLATracking)
class SLATrackingAdmin(admin.ModelAdmin):
    list_display = ['issue', 'first_response_breached', 'resolution_breached', 'created_at']
    list_filter = ['first_response_breached', 'resolution_breached']


@admin.register(EscalationLog)
class EscalationLogAdmin(admin.ModelAdmin):
    list_display = ['issue', 'escalated_at', 'acknowledged', 'acknowledged_by']
    list_filter = ['acknowledged', 'escalated_at']


@admin.register(EscalationRule)
class EscalationRuleAdmin(admin.ModelAdmin):
    list_display = ['name', 'trigger_condition', 'trigger_value', 'is_active']
    list_filter = ['trigger_condition', 'is_active']


@admin.register(IssueMetric)
class IssueMetricAdmin(admin.ModelAdmin):
    list_display = ['issue', 'time_to_first_contact', 'actual_resolution_time', 'reporter_satisfaction']
    list_filter = ['reporter_satisfaction']


@admin.register(AutomatedAction)
class AutomatedActionAdmin(admin.ModelAdmin):
    list_display = ['issue', 'action_type', 'triggered_at', 'accepted']
    list_filter = ['action_type', 'accepted']


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ['user_email', 'email_enabled', 'sms_enabled', 'push_enabled', 'digest_frequency']
