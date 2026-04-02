from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.db.models import Count, Q, Avg, F
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.html import strip_tags
from datetime import timedelta
import json
import re

from .models import Issue, IssueImage, IssueComment, IssueVote, IssueCategory, NotificationLog, Department
from .forms import SmartIssueForm, QuickReportForm, IssueCommentForm, IssueSearchForm
from tracking.models import StatusUpdate, SLATracking


def report_issue(request):
    """
    World-Class Issue Reporting View
    
    Features:
    - Smart form with real-time validation
    - GPS location detection
    - Voice input support (via browser)
    - Duplicate detection
    - Email confirmation
    - Image uploads
    """
    if request.method == 'POST':
        form = SmartIssueForm(request.POST, request.FILES)
        if form.is_valid():
            issue = form.save(commit=False)
            
            # Check for duplicates
            similar_issues = find_similar_issues(issue)
            if similar_issues.exists() and not request.POST.get('ignore_duplicates'):
                # Return duplicate warning
                return render(request, 'reporting/report_form.html', {
                    'form': form,
                    'duplicates': similar_issues[:5],
                    'show_duplicate_warning': True,
                })
            
            # Set initial status
            issue.status = 'submitted'
            issue.submitted_at = timezone.now()
            
            # Auto-assign to department based on issue type
            department = get_department_for_issue_type(issue.issue_type)
            if department:
                issue.assigned_department = department
            
            # Calculate SLA
            issue.sla_due_at = calculate_sla_due(issue)
            
            issue.save()
            
            # Handle image uploads - support both single 'image' and multiple 'images'
            images = request.FILES.getlist('image') or request.FILES.getlist('images')
            for i, img in enumerate(images):
                IssueImage.objects.create(
                    issue=issue,
                    image=img,
                    is_primary=(i == 0),
                    uploaded_by=issue.reporter_name,
                )
            
            # Send confirmation email
            send_issue_confirmation(issue)
            
            # Create SLA tracking record
            SLATracking.objects.create(
                issue=issue,
                target_first_response=4,
                target_resolution=get_resolution_time(issue),
            )
            
            messages.success(request, 
                f'✅ Issue reported successfully!<br>'
                f'<strong>Reference: {issue.tracking_code}</strong><br>'
                f'You will receive email updates as we work on your issue.')
            
            return redirect('tracking:issue_detail', pk=issue.pk)
    else:
        form = SmartIssueForm()
    
    return render(request, 'reporting/report_form.html', {
        'form': form,
        'categories': IssueCategory.objects.filter(is_active=True),
    })


def quick_report(request):
    """
    Quick mobile-friendly issue reporting
    """
    if request.method == 'POST':
        form = QuickReportForm(request.POST)
        if form.is_valid():
            # Create full issue from quick form
            issue = Issue.objects.create(
                title=f"Quick Report: {form.cleaned_data['issue_type']}",
                issue_type=form.cleaned_data['issue_type'],
                description=form.cleaned_data['description'],
                location=form.cleaned_data['location'],
                latitude=form.cleaned_data.get('latitude'),
                longitude=form.cleaned_data.get('longitude'),
                reporter_name='Mobile Reporter',
                reporter_email='mobile@kimberley.gov.za',
                status='submitted',
            )
            
            messages.success(request, f'Issue reported! Reference: {issue.tracking_code}')
            return redirect('tracking:issue_detail', pk=issue.pk)
    else:
        form = QuickReportForm()
    
    return render(request, 'reporting/quick_report.html', {'form': form})


def issue_list(request):
    """
    Enhanced Issue List with:
    - Advanced filtering
    - Real-time search
    - Statistics dashboard
    - Map view option
    """
    issues = Issue.objects.select_related('assigned_department').all()
    
    # Filters
    status_filter = request.GET.get('status')
    type_filter = request.GET.get('type')
    priority_filter = request.GET.get('priority')
    search_query = request.GET.get('q')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    ward = request.GET.get('ward')
    
    if status_filter:
        issues = issues.filter(status=status_filter)
    if type_filter:
        issues = issues.filter(issue_type=type_filter)
    if priority_filter:
        issues = issues.filter(priority=priority_filter)
    if search_query:
        issues = issues.filter(
            Q(tracking_code__icontains=search_query) |
            Q(title__icontains=search_query) |
            Q(location__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    if date_from:
        issues = issues.filter(created_at__date__gte=date_from)
    if date_to:
        issues = issues.filter(created_at__date__lte=date_to)
    if ward:
        issues = issues.filter(ward=ward)
    
    # Advanced Statistics
    stats = {
        'total': Issue.objects.count(),
        'pending': Issue.objects.filter(status='pending').count(),
        'in_progress': Issue.objects.filter(status='in_progress').count(),
        'resolved': Issue.objects.filter(status='resolved').count(),
        'closed': Issue.objects.filter(status='closed').count(),
        'breached_sla': Issue.objects.filter(sla_breached=True).count(),
        'avg_resolution_time': calculate_avg_resolution_time(),
    }
    
    # By type statistics
    type_stats = Issue.objects.values('issue_type').annotate(
        count=Count('id'),
        avg_time=Avg('created_at')
    ).order_by('-count')[:6]
    
    # By priority statistics
    priority_stats = Issue.objects.values('priority').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Pagination
    paginator = Paginator(issues, 20)
    page_number = request.GET.get('page')
    issues_page = paginator.get_page(page_number)
    
    # Search form
    search_form = IssueSearchForm(request.GET)
    
    return render(request, 'reporting/issue_list.html', {
        'issues': issues_page,
        'stats': stats,
        'type_stats': type_stats,
        'priority_stats': priority_stats,
        'status_filter': status_filter,
        'type_filter': type_filter,
        'priority_filter': priority_filter,
        'search_form': search_form,
        'total_pages': paginator.num_pages,
    })


def issue_detail_public(request, tracking_code):
    """
    Public issue detail view using tracking code
    """
    issue = get_object_or_404(Issue, tracking_code=tracking_code)
    status_updates = issue.status_updates.filter(public_visible=True).order_by('-timestamp')
    
    return render(request, 'reporting/issue_public.html', {
        'issue': issue,
        'status_updates': status_updates,
    })


@require_http_methods(["GET", "POST"])
def add_comment(request, pk):
    """
    Add a comment to an issue
    """
    issue = get_object_or_404(Issue, pk=pk)
    
    if request.method == 'POST':
        form = IssueCommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.issue = issue
            comment.save()
            
            messages.success(request, 'Comment added successfully!')
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'comment': {
                        'author': comment.author_name if not comment.is_anonymous else 'Anonymous',
                        'content': comment.content,
                        'created_at': comment.created_at.strftime('%b %d, %Y at %H:%M'),
                        'is_anonymous': comment.is_anonymous,
                    }
                })
            
            return redirect('tracking:issue_detail', pk=pk)
    else:
        form = IssueCommentForm()
    
    return render(request, 'reporting/add_comment.html', {
        'form': form,
        'issue': issue,
    })


@require_http_methods(["POST"])
def vote_issue(request, pk):
    """
    Vote on an issue (upvote/downvote)
    """
    issue = get_object_or_404(Issue, pk=pk)
    vote_type = request.POST.get('vote_type')
    voter_ip = get_client_ip(request)
    
    # Check if already voted
    existing_vote = IssueVote.objects.filter(issue=issue, voter_ip=voter_ip).first()
    
    if existing_vote:
        if existing_vote.vote_type == vote_type:
            # Remove vote
            existing_vote.delete()
            message = 'Vote removed'
        else:
            # Change vote
            existing_vote.vote_type = vote_type
            existing_vote.save()
            message = f'Vote changed to {vote_type}'
    else:
        # Create new vote
        IssueVote.objects.create(issue=issue, voter_ip=voter_ip, vote_type=vote_type)
        message = f'Thanks for your {vote_type}vote!'
    
    # Update issue counts
    issue.upvotes = issue.votes.filter(vote_type='up').count()
    issue.downvotes = issue.votes.filter(vote_type='down').count()
    issue.save()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'upvotes': issue.upvotes,
            'downvotes': issue.downvotes,
            'message': message,
        })
    
    messages.success(request, message)
    return redirect('tracking:issue_detail', pk=pk)


def track_issue(request):
    """
    Track issue status by tracking code
    """
    tracking_code = request.GET.get('code', '').upper().strip()
    
    if tracking_code:
        try:
            issue = Issue.objects.get(tracking_code=tracking_code)
            return redirect('tracking:issue_detail', pk=issue.pk)
        except Issue.DoesNotExist:
            messages.error(request, f'No issue found with tracking code: {tracking_code}')
    
    return render(request, 'reporting/track_issue.html')


from django.contrib.auth.models import User
from django.contrib.auth import login as auth_login

def register_view(request):
    """
    User registration view with KimConnect branding
    """
    if request.method == 'POST':
        # Get form data
        full_name = request.POST.get('full_name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        username = request.POST.get('username', '').strip()
        phone = request.POST.get('phone', '').strip()
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')
        ward = request.POST.get('ward', '')
        
        errors = []
        
        # Validation
        if not full_name:
            errors.append('Full name is required.')
        if not email:
            errors.append('Email is required.')
        if not username:
            errors.append('Username is required.')
        if len(password1) < 8:
            errors.append('Password must be at least 8 characters.')
        if password1 != password2:
            errors.append('Passwords do not match.')
        
        # Check if username exists
        if User.objects.filter(username=username).exists():
            errors.append('Username already exists.')
        if User.objects.filter(email=email).exists():
            errors.append('Email already registered.')
        
        if errors:
            return render(request, 'registration/register.html', {
                'errors': errors,
                'form_data': request.POST
            })
        
        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password1,
            first_name=full_name.split()[0] if full_name else '',
            last_name=' '.join(full_name.split()[1:]) if len(full_name.split()) > 1 else ''
        )
        
        # Log the user in
        auth_login(request, user)
        
        messages.success(request, f'Welcome to KimConnect, {full_name}! Your account has been created.')
        return redirect('home')
    
    return render(request, 'registration/register.html')


def home_view(request):
    """
    Home page with search, stats, and interactive map
    """
    import json
    
    # Statistics
    stats = {
        'total': Issue.objects.count(),
        'pending': Issue.objects.filter(status='pending').count(),
        'in_progress': Issue.objects.filter(status='in_progress').count(),
        'resolved': Issue.objects.filter(status='resolved').count(),
    }
    
    # Recent issues for display
    recent_issues = Issue.objects.filter(is_anonymous=False).order_by('-created_at')[:6]
    
    # Issues with coordinates for map
    map_issues = Issue.objects.filter(
        latitude__isnull=False,
        longitude__isnull=False
    ).order_by('-created_at')[:50]
    
    # Prepare map data
    map_issues_data = []
    for issue in map_issues:
        map_issues_data.append({
            'id': issue.id,
            'title': issue.title,
            'lat': float(issue.latitude) if issue.latitude else None,
            'lng': float(issue.longitude) if issue.longitude else None,
            'tracking_code': issue.tracking_code,
            'status': issue.status,
            'priority': issue.priority,
            'location': issue.location,
        })
    
    context = {
        'stats': stats,
        'recent_issues': recent_issues,
        'map_issues_json': json.dumps(map_issues_data),
        'google_maps_api_key': getattr(settings, 'GOOGLE_MAPS_API_KEY', ''),
    }
    
    return render(request, 'home.html', context)


@csrf_exempt
def api_report_issue(request):
    """
    API endpoint for mobile app integration
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Validate required fields
            required = ['title', 'issue_type', 'description', 'location', 'reporter_email']
            for field in required:
                if field not in data:
                    return JsonResponse({'error': f'Missing required field: {field}'}, status=400)
            
            # Create issue
            issue = Issue.objects.create(
                title=data['title'],
                issue_type=data['issue_type'],
                description=data['description'],
                location=data['location'],
                reporter_name=data.get('reporter_name', 'API Reporter'),
                reporter_email=data['reporter_email'],
                reporter_phone=data.get('reporter_phone', ''),
                latitude=data.get('latitude'),
                longitude=data.get('longitude'),
                priority=data.get('priority', 'medium'),
                status='submitted',
            )
            
            return JsonResponse({
                'success': True,
                'tracking_code': issue.tracking_code,
                'reference': issue.tracking_code,
                'created_at': issue.created_at.isoformat(),
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


def api_get_issue(request, tracking_code):
    """
    API endpoint to get issue details
    """
    try:
        issue = Issue.objects.get(tracking_code=tracking_code)
        updates = issue.status_updates.all().values(
            'message', 'new_status', 'updated_by', 'timestamp'
        )
        
        return JsonResponse({
            'success': True,
            'issue': {
                'tracking_code': issue.tracking_code,
                'title': issue.title,
                'status': issue.status,
                'status_display': issue.status_display,
                'priority': issue.priority,
                'location': issue.location,
                'created_at': issue.created_at.isoformat(),
                'estimated_resolution': issue.estimated_resolution.isoformat() if issue.estimated_resolution else None,
                'resolution_time': issue.resolution_time,
            },
            'updates': list(updates),
        })
    except Issue.DoesNotExist:
        return JsonResponse({'error': 'Issue not found'}, status=404)


# Helper Functions

def find_similar_issues(issue, threshold=0.7):
    """Find potentially duplicate issues"""
    return Issue.objects.filter(
        issue_type=issue.issue_type,
        status__in=['pending', 'in_progress'],
    ).filter(
        Q(location__icontains=extract_street_name(issue.location)) |
        Q(title__icontains=extract_keywords(issue.title))
    ).exclude(pk=issue.pk)[:5]


def extract_street_name(location):
    """Extract street name from location string"""
    # Simple extraction - in production, use geocoding API
    words = re.findall(r'\b[A-Za-z]+\b', location)
    return ' '.join(words[:2]) if len(words) >= 2 else location


def extract_keywords(title):
    """Extract keywords from title"""
    stop_words = {'the', 'a', 'an', 'on', 'in', 'at', 'road', 'street', 'ave', 'avenue'}
    words = re.findall(r'\b[A-Za-z]+\b', title.lower())
    return ' '.join([w for w in words if w not in stop_words and len(w) > 3])


def get_department_for_issue_type(issue_type):
    """Get responsible department for issue type"""
    department_map = {
        'water': 'Water & Sanitation',
        'electricity': 'Electrical Services',
        'pothole': 'Roads & Transport',
        'waste': 'Waste Management',
        'streetlight': 'Electrical Services',
        'drainage': 'Water & Sanitation',
        'noise': 'Environmental Health',
        'safety': 'Public Safety',
    }
    
    dept_name = department_map.get(issue_type)
    if dept_name:
        return Department.objects.filter(name__icontains=dept_name).first()
    return None


def calculate_sla_due(issue):
    """Calculate SLA due date based on priority"""
    priority_hours = {
        'critical': 4,
        'urgent': 24,
        'high': 48,
        'medium': 96,
        'low': 168,
    }
    hours = priority_hours.get(issue.priority, 48)
    return timezone.now() + timedelta(hours=hours)


def get_resolution_time(issue):
    """Get target resolution time based on issue type and priority"""
    base_times = {
        'water': 24,
        'electricity': 12,
        'pothole': 168,
        'waste': 48,
        'streetlight': 72,
    }
    
    priority_multiplier = {
        'critical': 0.25,
        'urgent': 0.5,
        'high': 0.75,
        'medium': 1.0,
        'low': 1.5,
    }
    
    base = base_times.get(issue.issue_type, 48)
    multiplier = priority_multiplier.get(issue.priority, 1.0)
    
    return int(base * multiplier)


def calculate_avg_resolution_time():
    """Calculate average resolution time in hours"""
    resolved = Issue.objects.filter(status='resolved', resolved_at__isnull=False)
    if not resolved.exists():
        return 0
    
    total_hours = 0
    count = 0
    for issue in resolved:
        if issue.resolution_time:
            total_hours += issue.resolution_time
            count += 1
    
    return round(total_hours / count, 1) if count > 0 else 0


def send_issue_confirmation(issue):
    """Send email confirmation when issue is reported"""
    try:
        subject = f'Issue Received - {issue.tracking_code}'
        
        context = {
            'issue': issue,
            'tracking_code': issue.tracking_code,
            'title': issue.title,
            'type': issue.get_issue_type_display(),
            'priority': issue.get_priority_display(),
            'estimated_response': calculate_sla_due(issue).strftime('%Y-%m-%d %H:%M'),
        }
        
        # HTML email
        html_content = render_to_string('email/issue_confirmation.html', context)
        text_content = strip_tags(html_content)
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[issue.reporter_email],
        )
        email.attach_alternative(html_content, 'text/html')
        email.send(fail_silently=True)
        
        # Log notification
        NotificationLog.objects.create(
            issue=issue,
            notification_type='confirmation',
            channel='email',
            recipient=issue.reporter_email,
            message=f'Issue {issue.tracking_code} confirmed',
            delivered=True,
        )
    except Exception as e:
        # Log error but don't fail
        NotificationLog.objects.create(
            issue=issue,
            notification_type='confirmation',
            channel='email',
            recipient=issue.reporter_email,
            message=f'Failed to send: {str(e)}',
            delivered=False,
            error_message=str(e),
        )


def get_client_ip(request):
    """Get client IP from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
