from django import forms
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.html import mark_safe
from django.utils.safestring import mark_safe as safe_mark
from .models import Issue, IssueImage, IssueComment, IssueVote, IssueCategory, Department
from crispy_forms.layout import Layout, Fieldset, Row, Column, Submit, HTML, Div
from crispy_forms.helper import FormHelper
import re


class SmartIssueForm(forms.ModelForm):
    """
    World-Class Issue Reporting Form
    
    Features:
    - Smart location detection
    - Voice input support
    - Image upload with preview
    - Anonymous reporting option
    - Smart priority suggestions
    - Duplicate detection
    """
    
    # Additional fields not in model
    use_current_location = forms.BooleanField(required=False, initial=False,
        label="Use my current location",
        help_text="Automatically detect your location using GPS")
    receive_updates = forms.BooleanField(required=False, initial=True,
        label="Receive status updates",
        help_text="Get notified when your issue status changes")
    share_location = forms.BooleanField(required=False, initial=False,
        label="Share precise location",
        help_text="Allow staff to see your exact location")
    agree_terms = forms.BooleanField(required=True,
        label="I agree to the terms of service",
        help_text="By submitting, you agree to our privacy policy and terms")
    
    # Coordinates (hidden fields for GPS data)
    latitude = forms.DecimalField(required=False, widget=forms.HiddenInput(), max_digits=10, decimal_places=7)
    longitude = forms.DecimalField(required=False, widget=forms.HiddenInput(), max_digits=10, decimal_places=7)
    location_accuracy = forms.DecimalField(required=False, widget=forms.HiddenInput(), max_digits=5, decimal_places=2)
    
    class Meta:
        model = Issue
        fields = [
            'title', 'issue_type', 'description', 'location', 
            'reporter_name', 'reporter_email', 'reporter_phone',
            'priority', 'is_anonymous', 'images'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full p-4 border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all',
                'placeholder': 'e.g., Water leak causing road flooding on Bultfontein Road',
                'maxlength': '200',
                'data-lpignore': 'true',
                'autocomplete': 'off'
            }),
            'issue_type': forms.Select(attrs={
                'class': 'w-full p-4 border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all bg-white',
                'data-placeholder': 'Select issue type...'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full p-4 border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all min-h-[150px]',
                'placeholder': 'Describe the issue in detail. Include when it started, how it affects you, and any safety concerns...',
                'rows': '5',
                'data-lpignore': 'true'
            }),
            'location': forms.TextInput(attrs={
                'class': 'w-full p-4 border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all',
                'placeholder': 'Enter street address or landmark (e.g., Bultfontein Rd & 5th Ave, Galeshewe)',
                'id': 'location-input',
                'autocomplete': 'off'
            }),
            'reporter_name': forms.TextInput(attrs={
                'class': 'w-full p-4 border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all',
                'placeholder': 'Your full name',
                'autocomplete': 'name'
            }),
            'reporter_email': forms.EmailInput(attrs={
                'class': 'w-full p-4 border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all',
                'placeholder': 'your.email@example.com',
                'autocomplete': 'email'
            }),
            'reporter_phone': forms.TextInput(attrs={
                'class': 'w-full p-4 border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all',
                'placeholder': '+27 XX XXX XXXX (optional)',
                'autocomplete': 'tel'
            }),
            'priority': forms.Select(attrs={
                'class': 'w-full p-4 border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all bg-white',
            }),
            'is_anonymous': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 text-blue-600 rounded border-gray-300 focus:ring-blue-500',
            }),
        }
        labels = {
            'title': 'Issue Title',
            'issue_type': 'Issue Type',
            'description': 'Description',
            'location': 'Location',
            'reporter_name': 'Your Name',
            'reporter_email': 'Email Address',
            'reporter_phone': 'Phone Number (Optional)',
            'priority': 'Priority Level',
            'is_anonymous': 'Report Anonymously',
        }
        help_texts = {
            'title': 'Be specific - include street name and nature of issue',
            'issue_type': 'Select the category that best describes your issue',
            'description': 'More details help us respond faster',
            'location': 'Include street name and nearest landmark for accuracy',
            'priority': 'Select urgent only for immediate safety hazards',
            'is_anonymous': 'Your personal information will be hidden from public view',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add priority descriptions
        priority_choices = [
            ('low', '🟢 Low - Minor inconvenience, can wait'),
            ('medium', '🟡 Medium - Affecting daily activities'),
            ('high', '🟠 High - Significant impact, needs attention'),
            ('urgent', '🔴 Urgent - Health/safety concern'),
            ('critical', '⚫ Critical - Emergency, immediate action needed'),
        ]
        self.fields['priority'].choices = priority_choices
        
        # Add help text with icons
        self.fields['title'].help_text = mark_safe('📝 Be specific - include street name and nature of issue')
        self.fields['issue_type'].help_text = mark_safe('🏷️ Select the category that best describes your issue')
        self.fields['description'].help_text = mark_safe('📋 More details help us respond faster')
        self.fields['location'].help_text = mark_safe('📍 Include street name and nearest landmark for accuracy')
        self.fields['priority'].help_text = mark_safe('⚠️ Select urgent only for immediate safety hazards')
        self.fields['is_anonymous'].help_text = mark_safe('🔒 Your personal information will be hidden from public view')
        
        # Make certain fields required
        self.fields['reporter_name'].required = True
        self.fields['reporter_email'].required = True
        
        # Set initial values
        self.fields['priority'].initial = 'medium'
    
    def clean_title(self):
        title = self.cleaned_data.get('title', '').strip()
        if len(title) < 10:
            raise forms.ValidationError('Title must be at least 10 characters for clarity')
        if len(title) > 200:
            raise forms.ValidationError('Title must be less than 200 characters')
        return title
    
    def clean_description(self):
        description = self.cleaned_data.get('description', '').strip()
        if len(description) < 20:
            raise forms.ValidationError('Please provide more details (at least 20 characters)')
        return description
    
    def clean_location(self):
        location = self.cleaned_data.get('location', '').strip()
        if len(location) < 5:
            raise forms.ValidationError('Please provide a more specific location')
        return location
    
    def clean_reporter_email(self):
        email = self.cleaned_data.get('reporter_email', '').strip().lower()
        if email:
            # Basic email validation
            pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(pattern, email):
                raise forms.ValidationError('Please enter a valid email address')
        return email
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Smart priority suggestion based on keywords
        title = cleaned_data.get('title', '').lower()
        description = cleaned_data.get('description', '').lower()
        combined_text = f"{title} {description}"
        
        # Critical keywords
        critical_keywords = ['emergency', 'danger', 'fire', 'flood', 'collapse', 'electrocution', 'gas leak', 'sewage overflow']
        urgent_keywords = ['urgent', 'broken', 'leak', 'no power', 'blocked', 'hazard', 'risk', 'accident']
        high_keywords = ['problem', 'issue', 'damaged', 'not working', 'broken', 'constant']
        
        if any(kw in combined_text for kw in critical_keywords):
            cleaned_data['suggested_priority'] = 'critical'
        elif any(kw in combined_text for kw in urgent_keywords):
            cleaned_data['suggested_priority'] = 'urgent'
        elif any(kw in combined_text for kw in high_keywords):
            cleaned_data['suggested_priority'] = 'high'
        
        # Check for anonymous reporting
        if cleaned_data.get('is_anonymous'):
            cleaned_data['reporter_name'] = 'Anonymous'
            cleaned_data['reporter_email'] = 'anonymous@kimberley.gov.za'
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Set notification preferences
        instance.notification_preferences = {
            'email': self.cleaned_data.get('receive_updates', True),
            'status_updates': True,
            'public_updates': not self.cleaned_data.get('is_anonymous', False),
        }
        
        # Set location coordinates if provided
        if self.cleaned_data.get('latitude'):
            instance.latitude = self.cleaned_data['latitude']
        if self.cleaned_data.get('longitude'):
            instance.longitude = self.cleaned_data['longitude']
        if self.cleaned_data.get('location_accuracy'):
            instance.location_accuracy = self.cleaned_data['location_accuracy']
        
        # Set AI-suggested priority
        if hasattr(self, 'cleaned_data') and self.cleaned_data.get('suggested_priority'):
            instance.suggested_priority = self.cleaned_data['suggested_priority']
        
        if commit:
            instance.save()
        
        return instance


class QuickReportForm(forms.Form):
    """Quick issue reporting form for mobile users"""
    issue_type = forms.ChoiceField(choices=[
        ('', 'Select issue type'),
        ('water', '💧 Water Leak'),
        ('electricity', '⚡ Electricity'),
        ('pothole', '🕳️ Pothole'),
        ('waste', '🗑️ Waste'),
        ('streetlight', '💡 Street Light'),
    ], widget=forms.Select(attrs={
        'class': 'w-full p-4 rounded-xl border-2 border-gray-200 focus:ring-2 focus:ring-blue-500',
        'data-mobile-friendly': 'true'
    }))
    location = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'w-full p-4 rounded-xl border-2 border-gray-200 focus:ring-2 focus:ring-blue-500',
        'placeholder': '📍 Your location',
        'id': 'quick-location'
    }), max_length=200)
    description = forms.CharField(widget=forms.Textarea(attrs={
        'class': 'w-full p-4 rounded-xl border-2 border-gray-200 focus:ring-2 focus:ring-blue-500',
        'placeholder': 'Brief description...',
        'rows': '3'
    }), max_length=500)
    latitude = forms.DecimalField(required=False, widget=forms.HiddenInput(), max_digits=10, decimal_places=7)
    longitude = forms.DecimalField(required=False, widget=forms.HiddenInput(), max_digits=10, decimal_places=7)
    
    def clean_location(self):
        location = self.cleaned_data.get('location', '').strip()
        if len(location) < 5:
            raise forms.ValidationError('Please provide a more specific location')
        return location


class IssueCommentForm(forms.ModelForm):
    """Form for community comments"""
    is_anonymous = forms.BooleanField(required=False, initial=False,
        label="Post anonymously",
        widget=forms.CheckboxInput(attrs={'class': 'w-4 h-4'}))
    
    class Meta:
        model = IssueComment
        fields = ['author_name', 'author_email', 'content', 'is_anonymous']
        widgets = {
            'author_name': forms.TextInput(attrs={
                'class': 'w-full p-3 border rounded-lg',
                'placeholder': 'Your name'
            }),
            'author_email': forms.EmailInput(attrs={
                'class': 'w-full p-3 border rounded-lg',
                'placeholder': 'your@email.com'
            }),
            'content': forms.Textarea(attrs={
                'class': 'w-full p-3 border rounded-lg',
                'placeholder': 'Share your thoughts...',
                'rows': '3'
            }),
        }
    
    def clean_content(self):
        content = self.cleaned_data.get('content', '').strip()
        if len(content) < 5:
            raise forms.ValidationError('Comment is too short')
        if len(content) > 1000:
            raise forms.ValidationError('Comment is too long (max 1000 characters)')
        return content


class IssueSearchForm(forms.Form):
    """Advanced search form"""
    query = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'class': 'w-full p-3 border rounded-lg',
        'placeholder': '🔍 Search by tracking code, title, or location...'
    }))
    status = forms.MultipleChoiceField(required=False, choices=[
        ('submitted', 'Submitted'),
        ('pending', 'Pending Review'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ], widget=forms.CheckboxSelectMultiple(attrs={'class': 'space-y-2'}))
    issue_type = forms.MultipleChoiceField(required=False, choices=[
        ('water', 'Water'),
        ('electricity', 'Electricity'),
        ('pothole', 'Pothole'),
        ('waste', 'Waste'),
        ('streetlight', 'Street Light'),
    ], widget=forms.CheckboxSelectMultiple(attrs={'class': 'space-y-2'}))
    priority = forms.MultipleChoiceField(required=False, choices=[
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
        ('critical', 'Critical'),
    ], widget=forms.CheckboxSelectMultiple(attrs={'class': 'space-y-2'}))
    date_from = forms.DateField(required=False, widget=forms.DateInput(attrs={
        'class': 'w-full p-3 border rounded-lg',
        'type': 'date'
    }))
    date_to = forms.DateField(required=False, widget=forms.DateInput(attrs={
        'class': 'w-full p-3 border rounded-lg',
        'type': 'date'
    }))
    ward = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'class': 'w-full p-3 border rounded-lg',
        'placeholder': 'Ward number'
    }))


class StaffAssignmentForm(forms.Form):
    """Form for staff to accept/claim issues"""
    staff_name = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'w-full p-3 border rounded-lg'
    }))
    department = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'w-full p-3 border rounded-lg'
    }))
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={
        'class': 'w-full p-3 border rounded-lg',
        'rows': '2',
        'placeholder': 'Additional notes (optional)'
    }))
