from django.db import models
from django.utils import timezone
from django.conf import settings
from reporting.models import Issue


STATUS_CHOICES = [
    ('submitted', 'Submitted'),
    ('pending', 'Pending Review'),
    ('in_progress', 'In Progress'),
    ('awaiting_parts', 'Awaiting Parts'),
    ('scheduled', 'Scheduled'),
    ('resolved', 'Resolved'),
    ('verified', 'Verified by Reporter'),
    ('closed', 'Closed'),
    ('rejected', 'Rejected'),
]

PRIORITY_CHOICES = [
    ('low', 'Low'),
    ('medium', 'Medium'),
    ('high', 'High'),
    ('urgent', 'Urgent'),
    ('critical', 'Critical'),
]


class StaffMember(models.Model):
    """Municipal staff members for issue assignment"""
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    department = models.CharField(max_length=100)
    role = models.CharField(max_length=50, choices=[
        ('technician', 'Technician'),
        ('supervisor', 'Supervisor'),
        ('manager', 'Manager'),
        ('admin', 'Administrator'),
    ])
    is_active = models.BooleanField(default=True)
    max_concurrent_issues = models.IntegerField(default=10)
    skills = models.JSONField(default=list, blank=True)
    current_load = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.department})"
    
    @property
    def available_capacity(self):
        return max(0, self.max_concurrent_issues - self.current_load)
    
    def increment_load(self):
        self.current_load = models.F('current_load') + 1
        self.save(update_fields=['current_load'])
    
    def decrement_load(self):
        self.current_load = models.F('current_load') - 1
        self.save(update_fields=['current_load'])


class StatusUpdate(models.Model):
    """
    Enhanced Status Update with Advanced Features
    
    Includes:
    - Status history with timestamps
    - Staff assignment tracking
    - Automated status changes
    - Rich media updates
    """
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name='status_updates')
    message = models.TextField()
    updated_by = models.CharField(max_length=100, help_text='Staff member name')
    staff_member = models.ForeignKey(StaffMember, on_delete=models.SET_NULL, 
                                     null=True, blank=True, related_name='updates')
    new_status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    previous_status = models.CharField(max_length=20, choices=STATUS_CHOICES, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Update metadata
    update_type = models.CharField(max_length=20, choices=[
        ('manual', 'Manual Update'),
        ('automatic', 'System Update'),
        ('escalation', 'Escalation'),
        ('sla', 'SLA Reminder'),
    ], default='manual')
    
    # Additional context
    estimated_completion = models.DateTimeField(null=True, blank=True)
    location_visited = models.BooleanField(default=False)
    photos_attached = models.IntegerField(default=0)
    public_visible = models.BooleanField(default=True)
    
    # Automation
    is_auto_generated = models.BooleanField(default=False)
    automation_rule = models.CharField(max_length=100, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Status Update'
        verbose_name_plural = 'Status Updates'
    
    def __str__(self):
        return f"Update for #{self.issue.tracking_code} - {self.new_status}"


class IssueAssignment(models.Model):
    """Track issue assignments to staff"""
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name='assignments')
    staff = models.ForeignKey(StaffMember, on_delete=models.CASCADE, related_name='assignments')
    assigned_at = models.DateTimeField(auto_now_add=True)
    assigned_by = models.CharField(max_length=100)
    is_primary = models.BooleanField(default=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-assigned_at']
        unique_together = ['issue', 'staff']
    
    def __str__(self):
        return f"{self.staff.name} assigned to {self.issue.tracking_code}"


class SLATracking(models.Model):
    """Service Level Agreement tracking"""
    issue = models.OneToOneField(Issue, on_delete=models.CASCADE, related_name='sla')
    
    # Target times (in hours)
    target_first_response = models.IntegerField(default=4)
    target_resolution = models.IntegerField(default=48)
    target_acknowledgement = models.IntegerField(default=2)
    
    # Actual times
    first_response_at = models.DateTimeField(null=True, blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    # Breach tracking
    first_response_breached = models.BooleanField(default=False)
    resolution_breached = models.BooleanField(default=False)
    acknowledgement_breached = models.BooleanField(default=False)
    
    # Notifications
    reminder_1_sent = models.BooleanField(default=False)  # 25% of time
    reminder_2_sent = models.BooleanField(default=False)  # 50% of time
    warning_sent = models.BooleanField(default=False)     # 75% of time
    breach_notice_sent = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'SLA Tracking'
        verbose_name_plural = 'SLA Trackings'
    
    def __str__(self):
        return f"SLA for {self.issue.tracking_code}"
    
    def check_breaches(self):
        """Check and update SLA breach status"""
        now = timezone.now()
        
        if self.first_response_at and not self.first_response_breached:
            target = self.acknowledged_at + timezone.timedelta(hours=self.target_first_response)
            if now > target:
                self.first_response_breached = True
        
        if self.resolved_at and not self.resolution_breached:
            target = self.issue.created_at + timezone.timedelta(hours=self.target_resolution)
            if now > target:
                self.resolution_breached = True
        
        return self.first_response_breached or self.resolution_breached


class EscalationRule(models.Model):
    """Define escalation rules for issues"""
    name = models.CharField(max_length=100)
    trigger_condition = models.CharField(max_length=50, choices=[
        ('time_in_status', 'Time in Status'),
        ('sla_breach', 'SLA Breach'),
        ('priority_change', 'Priority Change'),
        ('no_response', 'No Response'),
    ])
    trigger_value = models.IntegerField(help_text='Hours or count depending on condition')
    escalate_to_role = models.CharField(max_length=50)
    escalate_to_department = models.CharField(max_length=100)
    notify_original_owner = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} - {self.trigger_condition}"


class EscalationLog(models.Model):
    """Track all escalations"""
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name='escalations')
    rule = models.ForeignKey(EscalationRule, on_delete=models.SET_NULL, null=True)
    escalated_at = models.DateTimeField(auto_now_add=True)
    from_role = models.CharField(max_length=50, blank=True)
    to_role = models.CharField(max_length=50)
    reason = models.TextField()
    acknowledged = models.BooleanField(default=False)
    acknowledged_by = models.CharField(max_length=100, blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-escalated_at']
    
    def __str__(self):
        return f"Escalation for {self.issue.tracking_code} at {self.escalated_at}"


class IssueMetric(models.Model):
    """Track detailed metrics for analytics"""
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name='metrics')
    
    # Time metrics (in minutes)
    time_to_first_contact = models.IntegerField(null=True, blank=True)
    time_to_dispatch = models.IntegerField(null=True, blank=True)
    time_on_hold = models.IntegerField(default=0)
    actual_resolution_time = models.IntegerField(null=True, blank=True)
    
    # Quality metrics
    reporter_satisfaction = models.IntegerField(null=True, blank=True,
                                               choices=[(i, str(i)) for i in range(1, 6)])
    community_engagement = models.IntegerField(default=0)
    
    # Cost tracking
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    actual_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Resource usage
    staff_hours = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    materials_used = models.JSONField(default=list, blank=True)
    
    recorded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = 'Issue Metrics'
    
    def __str__(self):
        return f"Metrics for {self.issue.tracking_code}"


class AutomatedAction(models.Model):
    """Track automated actions taken on issues"""
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name='auto_actions')
    action_type = models.CharField(max_length=50, choices=[
        ('auto_assign', 'Auto Assignment'),
        ('auto_priority', 'Priority Update'),
        ('auto_category', 'Category Suggestion'),
        ('sla_reminder', 'SLA Reminder'),
        ('auto_close', 'Auto Closure'),
        ('duplicate_check', 'Duplicate Check'),
    ])
    action_taken = models.CharField(max_length=200)
    triggered_at = models.DateTimeField(auto_now_add=True)
    confidence = models.FloatField(null=True, blank=True)
    accepted = models.BooleanField(null=True, blank=True)
    accepted_by = models.CharField(max_length=100, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-triggered_at']
    
    def __str__(self):
        return f"{self.action_type} for {self.issue.tracking_code}"


class NotificationPreference(models.Model):
    """User notification preferences"""
    user_email = models.EmailField()
    notify_on_status_change = models.BooleanField(default=True)
    notify_on_progress = models.BooleanField(default=True)
    notify_on_resolution = models.BooleanField(default=True)
    notify_on_sla_breach = models.BooleanField(default=True)
    notify_on_community_activity = models.BooleanField(default=False)
    
    # Delivery preferences
    email_enabled = models.BooleanField(default=True)
    sms_enabled = models.BooleanField(default=False)
    push_enabled = models.BooleanField(default=False)
    digest_frequency = models.CharField(max_length=20, choices=[
        ('instant', 'Instant'),
        ('hourly', 'Hourly'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
    ], default='instant')
    
    quiet_hours_start = models.TimeField(null=True, blank=True)
    quiet_hours_end = models.TimeField(null=True, blank=True)
    
    class Meta:
        verbose_name_plural = 'Notification Preferences'
    
    def __str__(self):
        return f"Preferences for {self.user_email}"
