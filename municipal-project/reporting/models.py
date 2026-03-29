from django.db import models
from django.utils import timezone
from django.utils.text import slugify
import uuid
from decimal import Decimal

ISSUE_TYPES = [
    ('water', 'Water Leak'),
    ('electricity', 'Electricity Issue'),
    ('pothole', 'Pothole'),
    ('waste', 'Waste Management'),
    ('streetlight', 'Street Light'),
    ('drainage', 'Drainage Issue'),
    ('noise', 'Noise Complaint'),
    ('safety', 'Public Safety'),
    ('other', 'Other'),
]

PRIORITY_CHOICES = [
    ('low', 'Low'),
    ('medium', 'Medium'),
    ('high', 'High'),
    ('urgent', 'Urgent'),
    ('critical', 'Critical'),
]

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

VERIFICATION_STATUS = [
    ('none', 'Not Verified'),
    ('pending', 'Pending Verification'),
    ('verified', 'Community Verified'),
    ('disputed', 'Disputed'),
]


class IssueCategory(models.Model):
    """Dynamic issue categories with smart routing"""
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    icon = models.CharField(max_length=50, default='📍')
    color = models.CharField(max_length=7, default='#3B82F6')
    department = models.CharField(max_length=100, help_text='Responsible department')
    estimated_response_time = models.IntegerField(help_text='Hours to respond', default=48)
    auto_assign_to = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name_plural = 'Issue Categories'
        ordering = ['name']
    
    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.name


class Department(models.Model):
    """Municipal departments for issue routing"""
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    working_hours = models.CharField(max_length=100, default='Mon-Fri 08:00-16:30')
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.code})"


class Issue(models.Model):
    """
    Enhanced Issue Model with World-Class Features
    
    Includes:
    - Unique tracking codes
    - GPS coordinates
    - Multiple image attachments
    - Anonymous reporting
    - Community verification
    - SLA tracking
    - Smart priority suggestions
    """
    # Unique identifiers
    id = models.BigAutoField(primary_key=True)
    tracking_code = models.CharField(max_length=12, unique=True, editable=False, blank=True, null=True)
    slug = models.SlugField(max_length=150, blank=True)
    
    # Core issue information
    title = models.CharField(max_length=200, help_text='Clear, descriptive title')
    issue_type = models.CharField(max_length=20, choices=ISSUE_TYPES)
    category = models.ForeignKey(IssueCategory, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.TextField()
    
    # Location data
    location = models.CharField(max_length=200, help_text='Street address or landmark')
    location_description = models.TextField(blank=True, help_text='Additional location details')
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    location_accuracy = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True,
                                           help_text='GPS accuracy in meters')
    ward = models.CharField(max_length=20, blank=True, help_text='Municipal ward')
    suburb = models.CharField(max_length=100, blank=True)
    
    # Priority and status
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    suggested_priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, blank=True,
                                         help_text='AI-suggested priority')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='submitted')
    previous_status = models.CharField(max_length=20, choices=STATUS_CHOICES, blank=True)
    
    # Reporter information
    reporter_name = models.CharField(max_length=100)
    reporter_email = models.EmailField()
    reporter_phone = models.CharField(max_length=20, blank=True)
    is_anonymous = models.BooleanField(default=False)
    reporter_verified = models.BooleanField(default=False)
    notification_preferences = models.JSONField(default=dict, blank=True)
    
    # Media
    images = models.ManyToManyField('IssueImage', related_name='issue_images', blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(default=timezone.now)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    in_progress_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    estimated_resolution = models.DateTimeField(null=True, blank=True)
    
    # SLA tracking
    sla_due_at = models.DateTimeField(null=True, blank=True)
    sla_breached = models.BooleanField(default=False)
    sla_breach_notified = models.BooleanField(default=False)
    
    # Assignment
    assigned_department = models.ForeignKey(Department, on_delete=models.SET_NULL, 
                                           null=True, blank=True, related_name='assigned_issues')
    assigned_staff = models.CharField(max_length=100, blank=True)
    
    # Verification and community
    verification_status = models.CharField(max_length=20, choices=VERIFICATION_STATUS, default='none')
    upvotes = models.IntegerField(default=0)
    downvotes = models.IntegerField(default=0)
    reports_count = models.IntegerField(default=0, help_text='Times reported by community')
    
    # AI and metadata
    ai_category_suggestion = models.CharField(max_length=100, blank=True)
    ai_confidence_score = models.FloatField(null=True, blank=True)
    duplicate_of = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='duplicates')
    is_duplicate = models.BooleanField(default=False)
    is_accessible = models.BooleanField(default=True, help_text='ADA compliance')
    
    # Internal tracking
    external_reference = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    tags = models.JSONField(default=list, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Issue'
        verbose_name_plural = 'Issues'
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['priority', '-created_at']),
            models.Index(fields=['tracking_code']),
            models.Index(fields=['assigned_department', 'status']),
        ]
    
    def save(self, *args, **kwargs):
        if not self.tracking_code:
            self.tracking_code = self.generate_tracking_code()
        if not self.slug:
            self.slug = f"{self.tracking_code}-{slugify(self.title)[:50]}"
        super().save(*args, **kwargs)
    
    def generate_tracking_code(self):
        """Generate unique tracking code: SP-XXXXXX (Sol Plaatje)"""
        import random
        import string
        while True:
            code = f"SP-{''.join(random.choices(string.ascii_uppercase + string.digits, k=6))}"
            if not Issue.objects.filter(tracking_code=code).exists():
                return code
    
    def __str__(self):
        return f"{self.tracking_code} - {self.title}"
    
    @property
    def reference_number(self):
        """Public reference number for citizens"""
        return self.tracking_code
    
    @property
    def resolution_time(self):
        """Calculate resolution time in hours"""
        if self.resolved_at and self.created_at:
            delta = self.resolved_at - self.created_at
            return round(delta.total_seconds() / 3600, 1)
        return None
    
    @property
    def current_age(self):
        """Current age in hours"""
        if self.created_at:
            delta = timezone.now() - self.created_at
            return round(delta.total_seconds() / 3600, 1)
        return 0
    
    @property
    def status_display(self):
        """Human-readable status"""
        return dict(STATUS_CHOICES).get(self.status, self.status)
    
    @property
    def priority_emoji(self):
        """Priority indicator emoji"""
        emoji_map = {
            'low': '🟢',
            'medium': '🟡',
            'high': '🟠',
            'urgent': '🔴',
            'critical': '⚫',
        }
        return emoji_map.get(self.priority, '⚪')
    
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('tracking:issue_detail', kwargs={'pk': self.pk})


class IssueImage(models.Model):
    """Multiple image support for issues"""
    image = models.ImageField(upload_to='issues/%Y/%m/')
    caption = models.CharField(max_length=200, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_primary = models.BooleanField(default=False)
    uploaded_by = models.CharField(max_length=100, blank=True)
    
    def __str__(self):
        return f"Image for Issue - {self.uploaded_at.strftime('%Y-%m-%d %H:%M')}"


class IssueComment(models.Model):
    """Community comments on issues"""
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name='comments')
    author_name = models.CharField(max_length=100)
    author_email = models.EmailField()
    content = models.TextField()
    is_official = models.BooleanField(default=False)
    is_anonymous = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    is_hidden = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"Comment by {self.author_name} on {self.issue.tracking_code}"


class IssueVote(models.Model):
    """Community voting on issues"""
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name='votes')
    voter_ip = models.GenericIPAddressField()
    vote_type = models.CharField(max_length=10, choices=[('up', 'Upvote'), ('down', 'Downvote')])
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['issue', 'voter_ip']
    
    def __str__(self):
        return f"{self.vote_type} vote on {self.issue.tracking_code}"


class NotificationLog(models.Model):
    """Track all notifications sent"""
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=50)
    channel = models.CharField(max_length=20, choices=[
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('push', 'Push Notification'),
        ('in_app', 'In-App'),
    ])
    recipient = models.EmailField()
    message = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    delivered = models.BooleanField(default=False)
    delivered_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-sent_at']
    
    def __str__(self):
        return f"{self.notification_type} to {self.recipient} for {self.issue.tracking_code}"
