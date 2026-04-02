from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
import json
from .models import StatusUpdate, IssueAssignment, SLATracking
from reporting.models import Issue


from django.contrib.auth.decorators import login_required

@login_required(login_url='/login/')
@staff_member_required
def dashboard(request):
    """Staff dashboard with real-time statistics and overview"""
    from .models import StaffMember

    
    # Get all issues for statistics
    issues = Issue.objects.all().order_by('-created_at')
    
    # Calculate statistics
    stats = {
        'total': issues.count(),
        'pending': issues.filter(status='pending').count(),
        'in_progress': issues.filter(status='in_progress').count(),
        'resolved': issues.filter(status='resolved').count(),
    }
    
    # Critical issues (urgent priority)
    critical_issues = issues.filter(
        priority='urgent',
        status__in=['pending', 'in_progress']
    ).order_by('-created_at')
    
    # SLA warnings (issues approaching deadline)
    sla_warnings = []
    now = timezone.now()
    for issue in issues.filter(status__in=['pending', 'in_progress']).exclude(priority='urgent'):
        # Calculate SLA based on priority
        sla_hours = {'high': 24, 'medium': 72, 'low': 168}.get(issue.priority, 72)
        deadline = issue.created_at + timedelta(hours=sla_hours)
        time_left = deadline - now
        
        # Warning if less than 25% time remaining
        if time_left.total_seconds() < (sla_hours * 3600 * 0.25) and time_left.total_seconds() > 0:
            sla_warnings.append(issue)
    
    # Get recent status updates
    recent_updates = StatusUpdate.objects.select_related('issue').order_by('-timestamp')[:10]
    
    # Issue list with filters
    status_filter = request.GET.get('status', '')
    priority_filter = request.GET.get('priority', '')
    type_filter = request.GET.get('type', '')
    
    filtered_issues = Issue.objects.all()
    if status_filter:
        filtered_issues = filtered_issues.filter(status=status_filter)
    if priority_filter:
        filtered_issues = filtered_issues.filter(priority=priority_filter)
    if type_filter:
        filtered_issues = filtered_issues.filter(issue_type=type_filter)
    
    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(filtered_issues, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Chart data - Issues by type (for JavaScript)
    type_distribution = Issue.objects.values('issue_type').annotate(count=Count('id'))
    type_labels = [item['issue_type'].title() for item in type_distribution]
    type_data = [item['count'] for item in type_distribution]
    
    context = {
        'stats': stats,
        'issues': page_obj,
        'critical_issues': critical_issues,
        'sla_warnings': sla_warnings,
        'recent_updates': recent_updates,
        'staff_members': StaffMember.objects.filter(is_active=True),
        'type_labels_json': json.dumps(type_labels),
        'type_data_json': json.dumps(type_data),
    }
    
    return render(request, 'tracking/dashboard.html', context)



def issue_detail(request, issue_id):
    """Detailed view of a single issue with status timeline"""
    issue = get_object_or_404(Issue, id=issue_id)
    
    # Get status updates ordered chronologically
    status_updates = issue.status_updates.all().order_by('timestamp')
    
    # Check if user can update status (staff only)
    can_update = request.user.is_staff
    
    # Handle status update form submission
    if request.method == 'POST' and can_update:
        message = request.POST.get('message', '').strip()
        new_status = request.POST.get('status', '')
        
        if message and new_status:
            StatusUpdate.objects.create(
                issue=issue,
                message=message,
                previous_status=issue.status,
                new_status=new_status,
                updated_by=request.user.username if request.user.is_authenticated else 'Staff'
            )
            issue.status = new_status
            issue.save()
            messages.success(request, f'Status updated to {issue.get_status_display()}')
            return redirect('tracking:issue_detail', issue_id=issue.id)
    
    # Calculate SLA info
    now = timezone.now()
    sla_hours = {'urgent': 4, 'high': 24, 'medium': 72, 'low': 168}.get(issue.priority, 72)
    deadline = issue.created_at + timedelta(hours=sla_hours)
    time_remaining = deadline - now
    
    # Determine SLA status
    if issue.status in ['resolved', 'closed']:
        sla_status = 'completed'
        sla_display = 'SLA Completed'
    elif time_remaining.total_seconds() <= 0:
        sla_status = 'breached'
        sla_display = f'SLA Breached by {abs(int(time_remaining.total_seconds() / 3600))}h'
    elif time_remaining.total_seconds() < (sla_hours * 3600 * 0.25):
        sla_status = 'critical'
        sla_display = f'{int(time_remaining.total_seconds() / 3600)}h remaining'
    elif time_remaining.total_seconds() < (sla_hours * 3600 * 0.5):
        sla_status = 'warning'
        sla_display = f'{int(time_remaining.total_seconds() / 3600)}h remaining'
    else:
        sla_status = 'on_track'
        sla_display = f'{int(time_remaining.total_seconds() / 3600)}h remaining'
    
    # Get voting stats
    upvotes = issue.votes.filter(vote_type='up').count()
    downvotes = issue.votes.filter(vote_type='down').count()
    
    context = {
        'issue': issue,
        'status_updates': status_updates,
        'can_update': can_update,
        'sla_status': sla_status,
        'sla_display': sla_display,
        'sla_deadline': deadline,
        'upvotes': upvotes,
        'downvotes': downvotes,
        'priority_choices': Issue.PRIORITY_CHOICES,
        'status_choices': Issue.STATUS_CHOICES,
    }
    
    return render(request, 'tracking/issue_detail.html', context)


@staff_member_required
def assign_issue(request, issue_id):
    """Assign an issue to a department/staff member"""
    issue = get_object_or_404(Issue, id=issue_id)
    
    if request.method == 'POST':
        department = request.POST.get('department', '')
        notes = request.POST.get('notes', '')
        
        # Create assignment
        IssueAssignment.objects.create(
            issue=issue,
            assigned_to=department,
            assigned_by=request.user.username,
            notes=notes
        )
        
        # Update issue status
        issue.status = 'in_progress'
        issue.department = department
        issue.save()
        
        # Create status update
        StatusUpdate.objects.create(
            issue=issue,
            message=f'Issue assigned to {department}',
            previous_status='pending',
            new_status='in_progress',
            updated_by=request.user.username
        )
        
        messages.success(request, f'Issue assigned to {department}')
    
    return redirect('tracking:issue_detail', issue_id=issue.id)


@staff_member_required
def escalate_issue(request, issue_id):
    """Escalate an issue to higher priority"""
    issue = get_object_or_404(Issue, id=issue_id)
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        escalate_to = request.POST.get('escalate_to', 'supervisor')
        
        # Create status update
        StatusUpdate.objects.create(
            issue=issue,
            message=f'Issue escalated to {escalate_to}. Reason: {reason}',
            previous_status=issue.status,
            new_status=issue.status,
            updated_by=request.user.username
        )
        
        messages.warning(request, 'Issue has been escalated')
    
    return redirect('tracking:issue_detail', issue_id=issue.id)


def public_dashboard(request):
    """Public-facing dashboard for residents to view community issues"""
    # Get public issues
    issues = Issue.objects.filter(is_anonymous=False).exclude(
        status__in=['resolved', 'closed']
    ).order_by('-created_at')[:50]
    
    # Statistics
    stats = {
        'total': Issue.objects.count(),
        'pending': Issue.objects.filter(status='pending').count(),
        'in_progress': Issue.objects.filter(status='in_progress').count(),
        'resolved': Issue.objects.filter(status='resolved').count(),
    }
    
    context = {
        'issues': issues,
        'stats': stats,
    }
    
    return render(request, 'tracking/public_dashboard.html', context)


# API Endpoints for real-time updates
def api_stats(request):
    """API endpoint for real-time statistics (used for SSE/long polling)"""
    stats = {
        'total': Issue.objects.count(),
        'pending': Issue.objects.filter(status='pending').count(),
        'in_progress': Issue.objects.filter(status='in_progress').count(),
        'resolved': Issue.objects.filter(status='resolved').count(),
        'timestamp': timezone.now().isoformat()
    }
    return JsonResponse(stats)


def api_issue_updates(request):
    """API endpoint for recent issue updates"""
    since = request.GET.get('since')
    if since:
        since_time = timezone.datetime.fromisoformat(since)
    else:
        since_time = timezone.now() - timedelta(minutes=5)
    
    updates = StatusUpdate.objects.filter(timestamp__gte=since_time).select_related('issue')
    
    data = [{
        'id': u.id,
        'issue_id': u.issue.id,
        'tracking_code': u.issue.tracking_code,
        'message': u.message,
        'new_status': u.new_status,
        'created_at': u.timestamp.isoformat()
    } for u in updates]
    
    return JsonResponse({'updates': data, 'timestamp': timezone.now().isoformat()})


def dashboard_stats_json(request):
    """JSON endpoint for dashboard statistics"""
    issues = Issue.objects.all()
    
    stats = {
        'total': issues.count(),
        'pending': issues.filter(status='pending').count(),
        'in_progress': issues.filter(status='in_progress').count(),
        'resolved': issues.filter(status='resolved').count(),
        'by_type': {},
        'by_priority': {},
    }
    
    # By type
    type_dist = issues.values('issue_type').annotate(count=Count('id'))
    for item in type_dist:
        stats['by_type'][item['issue_type']] = item['count']
    
    # By priority
    priority_dist = issues.values('priority').annotate(count=Count('id'))
    for item in priority_dist:
        stats['by_priority'][item['priority']] = item['count']
    
    return JsonResponse(stats)


@staff_member_required
def update_status(request, pk):
    """Update issue status via AJAX"""
    issue = get_object_or_404(Issue, pk=pk)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        message = request.POST.get('message', f'Status updated to {new_status}')
        
        if new_status:
            old_status = issue.status
            issue.status = new_status
            issue.save()
            
            # Create status update record
            StatusUpdate.objects.create(
                issue=issue,
                message=message,
                previous_status=old_status,
                new_status=new_status,
                updated_by=request.user.username if request.user.is_authenticated else 'Staff'
            )
            
            messages.success(request, f'Issue status updated to {issue.get_status_display()}')
    
    return redirect('tracking:issue_detail', pk=pk)


@staff_member_required
def assign_staff(request, pk):
    """Assign issue to staff member"""
    issue = get_object_or_404(Issue, pk=pk)
    
    if request.method == 'POST':
        staff_name = request.POST.get('staff_name')
        department = request.POST.get('department')
        
        IssueAssignment.objects.create(
            issue=issue,
            assigned_to=staff_name or department,
            assigned_by=request.user.username,
            notes=request.POST.get('notes', '')
        )
        
        issue.status = 'in_progress'
        issue.department = department
        issue.save()
        
        StatusUpdate.objects.create(
            issue=issue,
            message=f'Assigned to {staff_name or department}',
            previous_status='pending',
            new_status='in_progress',
            updated_by=request.user.username
        )
        
        messages.success(request, 'Issue assigned successfully')
    
    return redirect('tracking:issue_detail', pk=pk)


@staff_member_required
def escalate_issue(request, pk):
    """Escalate issue to higher priority"""
    issue = get_object_or_404(Issue, pk=pk)
    
    if request.method == 'POST':
        reason = request.POST.get('reason', 'Escalated by supervisor')
        
        StatusUpdate.objects.create(
            issue=issue,
            message=f'Issue escalated: {reason}',
            previous_status=issue.status,
            new_status=issue.status,
            updated_by=request.user.username
        )
        
        messages.warning(request, 'Issue has been escalated')
    
    return redirect('tracking:issue_detail', pk=pk)


def issue_timeline_sse(request, pk):
    """Server-Sent Events for real-time timeline updates"""
    from django.http import StreamingHttpResponse
    import time
    
    issue = get_object_or_404(Issue, pk=pk)
    last_update = issue.status_updates.order_by('-timestamp').first()
    last_timestamp = last_update.timestamp.isoformat() if last_update else ''
    
    def event_stream():
        while True:
            # Check for new updates
            latest = issue.status_updates.order_by('-timestamp').first()
            if latest and latest.timestamp.isoformat() > last_timestamp:
                yield f"data: {json.dumps({'message': latest.message, 'status': latest.new_status, 'by': latest.updated_by})}\n\n"
            time.sleep(2)  # Poll every 2 seconds
    
    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


@staff_member_required
def analytics_view(request):
    """Analytics dashboard for staff with comprehensive data"""
    from django.db.models.functions import TruncDate, TruncWeek
    from datetime import datetime, timedelta
    
    now = timezone.now()
    thirty_days_ago = now - timedelta(days=30)
    
    # Core statistics
    total_reports = Issue.objects.count()
    resolved_count = Issue.objects.filter(status='resolved').count()
    resolution_rate = round((resolved_count / total_reports * 100) if total_reports > 0 else 0)
    new_this_month = Issue.objects.filter(created_at__gte=thirty_days_ago).count()
    
    # Resolution time analysis
    resolution_hours = []
    resolved_issues = Issue.objects.filter(status='resolved', resolved_at__isnull=False)
    for issue in resolved_issues[:200]:
        if issue.resolved_at and issue.created_at:
            hours = (issue.resolved_at - issue.created_at).total_seconds() / 3600
            resolution_hours.append(hours)
    avg_response_time = round(sum(resolution_hours) / len(resolution_hours), 1) if resolution_hours else 0
    
    # Mock satisfaction data (would come from reviews/ratings table)
    satisfaction_rate = 87
    reviews_count = 156
    
    # Issue types distribution
    type_dist = Issue.objects.values('issue_type').annotate(count=Count('id')).order_by('-count')
    issue_types = {
        'labels': json.dumps([item['issue_type'].title() for item in type_dist]),
        'data': json.dumps([item['count'] for item in type_dist])
    }
    
    # Weekly trend (last 7 weeks)
    weekly_labels = []
    weekly_data = []
    resolved_data = []
    for i in range(6, -1, -1):
        week_start = now - timedelta(weeks=i, days=now.weekday())
        week_end = week_start + timedelta(days=7)
        week_issues = Issue.objects.filter(created_at__gte=week_start, created_at__lt=week_end)
        weekly_labels.append(week_start.strftime('%b %d'))
        weekly_data.append(week_issues.count())
        resolved_data.append(week_issues.filter(status='resolved').count())
    
    # Status distribution
    status_dist = Issue.objects.values('status').annotate(count=Count('id'))
    status_labels = json.dumps([s['status'].title().replace('_', ' ') for s in status_dist])
    status_data = json.dumps([s['count'] for s in status_dist])
    
    # Ward statistics
    ward_dist = Issue.objects.exclude(ward='').values('ward').annotate(count=Count('id')).order_by('-count')[:5]
    total_area = sum(w['count'] for w in ward_dist) if ward_dist else 1
    ward_stats = [{
        'name': w['ward'].title() if w['ward'] else 'Unknown',
        'count': w['count'],
        'percentage': round((w['count'] / total_area * 100) if total_area > 0 else 0)
    } for w in ward_dist]
    
    context = {
        'now': now,
        'total_reports': total_reports,
        'resolved_count': resolved_count,
        'resolution_rate': resolution_rate,
        'new_this_month': new_this_month,
        'avg_response_time': avg_response_time,
        'satisfaction_rate': satisfaction_rate,
        'reviews_count': reviews_count,
        'issue_types': issue_types,
        'weekly_labels': json.dumps(weekly_labels),
        'weekly_data': json.dumps(weekly_data),
        'resolved_data': json.dumps(resolved_data),
        'status_labels': status_labels,
        'status_data': status_data,
        'ward_stats': ward_stats,
    }
    
    return render(request, 'tracking/analytics.html', context)
