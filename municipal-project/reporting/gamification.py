"""
Gamification System for KimConnect
Rewards community engagement and issue reporting
"""

import random
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta


class UserBadge(models.Model):
    """User achievement badges"""
    BADGE_TYPES = [
        ('first_report', 'First Report', '🎯'),
        ('reporter_5', 'Active Reporter', '📝'),
        ('reporter_25', 'Dedicated Reporter', '🏆'),
        ('reporter_100', 'Community Champion', '🌟'),
        ('streak_7', 'Week Warrior', '🔥'),
        ('streak_30', 'Month Master', '💪'),
        ('resolved_10', 'Problem Solver', '🔧'),
        ('verified', 'Verified Citizen', '✅'),
        ('helper', 'Good Samaritan', '🤝'),
        ('early_bird', 'Early Bird', '🐦'),
        ('night_owl', 'Night Owl', '🦉'),
        ('photographer', 'Photo Pro', '📸'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='badges')
    badge_type = models.CharField(max_length=50, choices=[(b[0], b[1]) for b in BADGE_TYPES])
    earned_at = models.DateTimeField(auto_now_add=True)
    display_order = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-earned_at']
        unique_together = ['user', 'badge_type']
    
    def __str__(self):
        return f"{self.user.username} - {self.get_badge_type_display()}"
    
    @classmethod
    def get_badge_info(cls, badge_type):
        for b in cls.BADGE_TYPES:
            if b[0] == badge_type:
                return {'name': b[1], 'emoji': b[2]}
        return {'name': badge_type, 'emoji': '🏅'}


class UserPoints(models.Model):
    """Track user points and level"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='points')
    points = models.IntegerField(default=0)
    level = models.IntegerField(default=1)
    streak_days = models.IntegerField(default=0)
    last_report_date = models.DateField(null=True, blank=True)
    total_reports = models.IntegerField(default=0)
    total_resolved = models.IntegerField(default=0)
    
    # Achievement stats
    reports_this_week = models.IntegerField(default=0)
    reports_this_month = models.IntegerField(default=0)
    
    class Meta:
        verbose_name_plural = "User Points"
    
    def __str__(self):
        return f"{self.user.username}: {self.points} points (Level {self.level})"
    
    def add_points(self, amount: int, reason: str):
        """Add points and check for level up"""
        self.points += amount
        
        # Level up every 100 points
        new_level = (self.points // 100) + 1
        leveled_up = new_level > self.level
        
        if leveled_up:
            self.level = new_level
        
        self.save()
        
        return {
            'new_points': self.points,
            'level': self.level,
            'leveled_up': leveled_up
        }
    
    def check_streak(self):
        """Update streak based on reporting activity"""
        today = timezone.now().date()
        
        if self.last_report_date:
            days_diff = (today - self.last_report_date).days
            
            if days_diff == 1:
                self.streak_days += 1
            elif days_diff > 1:
                self.streak_days = 1
        else:
            self.streak_days = 1
        
        self.last_report_date = today
        self.save()
        
        return self.streak_days


class PointTransaction(models.Model):
    """Log all point transactions"""
    ACTIONS = [
        ('report_submitted', 'Report Submitted', 10),
        ('report_accepted', 'Report Accepted', 5),
        ('report_resolved', 'Report Resolved', 25),
        ('photo_uploaded', 'Photo Uploaded', 5),
        ('verified_issue', 'Issue Verified', 10),
        ('streak_bonus', 'Streak Bonus', 15),
        ('level_bonus', 'Level Up Bonus', 50),
        ('badge_earned', 'Badge Earned', 20),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='point_transactions')
    action = models.CharField(max_length=50)
    points = models.IntegerField()
    description = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username}: {self.points:+d} for {self.action}"


class Leaderboard:
    """Leaderboard calculations"""
    
    @staticmethod
    def get_top_reporters(limit: int = 10, timeframe: str = 'all'):
        """Get top reporters for leaderboard"""
        from django.db.models import Sum, Count
        
        qs = UserPoints.objects.all()
        
        if timeframe == 'week':
            # Filter users who reported in the last 7 days
            week_ago = timezone.now() - timedelta(days=7)
            qs = qs.filter(
                point_transactions__created_at__gte=week_ago
            ).annotate(
                recent_reports=Count('point_transactions', 
                                   filter=models.Q(point_transactions__action='report_submitted',
                                                  point_transactions__created_at__gte=week_ago))
            ).order_by('-recent_reports')[:limit]
        elif timeframe == 'month':
            month_ago = timezone.now() - timedelta(days=30)
            qs = qs.filter(
                point_transactions__created_at__gte=month_ago
            ).annotate(
                recent_reports=Count('point_transactions',
                                   filter=models.Q(point_transactions__action='report_submitted',
                                                  point_transactions__created_at__gte=month_ago))
            ).order_by('-recent_reports')[:limit]
        else:
            qs = qs.order_by('-points')[:limit]
        
        return [
            {
                'rank': i + 1,
                'user': up.user,
                'username': up.user.username,
                'points': up.points,
                'level': up.level,
                'reports': up.total_reports,
                'badges': up.user.badges.count()
            }
            for i, up in enumerate(qs)
        ]
    
    @staticmethod
    def get_user_rank(user: User) -> dict:
        """Get user's current rank"""
        from django.db.models import Count
        
        # Get user's points
        try:
            user_points = UserPoints.objects.get(user=user)
            points = user_points.points
        except UserPoints.DoesNotExist:
            points = 0
        
        # Count users with more points
        rank = UserPoints.objects.filter(points__gt=points).count() + 1
        total_users = UserPoints.objects.count()
        
        return {
            'rank': rank,
            'total_users': total_users,
            'percentile': round((1 - rank / total_users) * 100) if total_users > 0 else 100,
            'points': points
        }


def award_points(user: User, action: str, description: str = None) -> dict:
    """Award points to user for various actions"""
    from django.db import transaction
    
    # Get points value for action
    action_points = dict(PointTransaction.ACTIONS)
    points = action_points.get(action, 0)
    
    if points == 0:
        return {'success': False, 'reason': 'Unknown action'}
    
    with transaction.atomic():
        # Get or create user points
        user_points, _ = UserPoints.objects.get_or_create(user=user)
        
        # Add points
        result = user_points.add_points(points, action)
        
        # Log transaction
        desc = description or f"Points for {action}"
        PointTransaction.objects.create(
            user=user,
            action=action,
            points=points,
            description=desc
        )
        
        # Update report counts
        if 'report' in action:
            user_points.total_reports += 1
            user_points.reports_this_week += 1
            user_points.reports_this_month += 1
            user_points.save()
            
            # Check for streak
            streak = user_points.check_streak()
            
            # Award streak badge
            if streak >= 7 and not UserBadge.objects.filter(user=user, badge_type='streak_7').exists():
                award_badge(user, 'streak_7')
            if streak >= 30 and not UserBadge.objects.filter(user=user, badge_type='streak_30').exists():
                award_badge(user, 'streak_30')
        
        # Award first report badge
        if user_points.total_reports == 1:
            if not UserBadge.objects.filter(user=user, badge_type='first_report').exists():
                award_badge(user, 'first_report')
        
        # Award reporter badges
        report_badges = {5: 'reporter_5', 25: 'reporter_25', 100: 'reporter_100'}
        for count, badge in report_badges.items():
            if user_points.total_reports >= count:
                if not UserBadge.objects.filter(user=user, badge_type=badge).exists():
                    award_badge(user, badge)
    
    return {
        'success': True,
        'points_earned': points,
        **result
    }


def award_badge(user: User, badge_type: str) -> UserBadge:
    """Award a badge to user"""
    badge, created = UserBadge.objects.get_or_create(
        user=user,
        badge_type=badge_type
    )
    
    if created:
        # Award bonus points for badge
        award_points(user, 'badge_earned', f"Earned badge: {badge.get_badge_type_display()}")
        
        # Award level bonus on milestone badges
        if badge_type in ['reporter_25', 'reporter_100', 'community_champion']:
            award_points(user, 'level_bonus', "Milestone badge bonus")
    
    return badge


def check_time_based_badges(user: User):
    """Check and award time-based badges"""
    hour = timezone.now().hour
    
    # Early bird (5 AM - 8 AM)
    if 5 <= hour < 8:
        if not UserBadge.objects.filter(user=user, badge_type='early_bird').exists():
            award_badge(user, 'early_bird')
    
    # Night owl (10 PM - 4 AM)
    if hour >= 22 or hour < 4:
        if not UserBadge.objects.filter(user=user, badge_type='night_owl').exists():
            award_badge(user, 'night_owl')


# Leaderboard levels
LEVELS = [
    (1, 'Newcomer', '🌱', 0),
    (2, 'Citizen', '🏠', 100),
    (3, 'Reporter', '📝', 200),
    (4, 'Advocate', '🗣️', 400),
    (5, 'Helper', '🤝', 700),
    (6, 'Champion', '🏆', 1000),
    (7, 'Hero', '🦸', 1500),
    (8, 'Legend', '👑', 2500),
    (9, 'Guardian', '🛡️', 4000),
    (10, 'Kimberley Hero', '⭐', 6000),
]


def get_level_info(level: int) -> dict:
    """Get level information"""
    for l in LEVELS:
        if l[0] == level:
            return {
                'level': l[0],
                'name': l[1],
                'emoji': l[2],
                'points_needed': l[3]
            }
    return {'level': level, 'name': 'Unknown', 'emoji': '🏅', 'points_needed': 0}


def get_next_level(level: int) -> dict:
    """Get next level information"""
    for i, l in enumerate(LEVELS):
        if l[0] == level and i + 1 < len(LEVELS):
            return {
                'level': LEVELS[i + 1][0],
                'name': LEVELS[i + 1][1],
                'emoji': LEVELS[i + 1][2],
                'points_needed': LEVELS[i + 1][3]
            }
    return None
