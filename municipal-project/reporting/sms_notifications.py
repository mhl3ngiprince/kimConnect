"""
SMS Notification System for KimConnect
Supports Twilio and other SMS providers
"""

from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class SMSProvider:
    """Base class for SMS providers"""
    
    def send(self, phone_number: str, message: str) -> bool:
        """Send SMS to phone number"""
        raise NotImplementedError
    
    def send_template(self, phone_number: str, template_name: str, context: dict) -> bool:
        """Send SMS using template"""
        raise NotImplementedError


class TwilioSMSProvider(SMSProvider):
    """Twilio SMS integration"""
    
    def __init__(self):
        self.account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', '')
        self.auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', '')
        self.from_number = getattr(settings, 'TWILIO_FROM_NUMBER', '')
        
    def send(self, phone_number: str, message: str) -> bool:
        """Send SMS via Twilio"""
        if not all([self.account_sid, self.auth_token, self.from_number]):
            logger.warning("Twilio not configured, skipping SMS")
            return False
            
        try:
            from twilio.rest import Client
            client = Client(self.account_sid, self.auth_token)
            
            # Format phone number
            phone = self._format_phone(phone_number)
            
            message = client.messages.create(
                body=message[:1600],  # SMS limit
                from_=self.from_number,
                to=phone
            )
            
            logger.info(f"SMS sent to {phone}: {message.sid}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send SMS: {e}")
            return False
    
    def send_template(self, phone_number: str, template_name: str, context: dict) -> bool:
        """Send SMS using template"""
        try:
            # Load template and render
            template_path = f"sms/{template_name}.txt"
            message = render_to_string(template_path, context)
            return self.send(phone_number, message)
        except Exception as e:
            logger.error(f"Failed to send SMS template: {e}")
            return False
    
    def _format_phone(self, phone: str) -> str:
        """Format phone number for Twilio"""
        # Remove spaces, dashes
        phone = ''.join(c for c in phone if c.isdigit() or c == '+')
        
        # Add country code if missing
        if not phone.startswith('+'):
            if phone.startswith('0'):
                phone = '+27' + phone[1:]
            elif phone.startswith('71') or phone.startswith('72') or phone.startswith('73') or phone.startswith('74') or phone.startswith('76') or phone.startswith('78') or phone.startswith('81'):
                phone = '+27' + phone
            else:
                phone = '+27' + phone
        
        return phone


class AfricaTalkingSMSProvider(SMSProvider):
    """Africa's Talking SMS integration (popular in South Africa)"""
    
    def __init__(self):
        self.api_key = getattr(settings, 'AFRICA_TALKING_API_KEY', '')
        self.username = getattr(settings, 'AFRICA_TALKING_USERNAME', 'sandbox')
        self.short_code = getattr(settings, 'AFRICA_TALKING_SHORT_CODE', '')
        
    def send(self, phone_number: str, message: str) -> bool:
        """Send SMS via Africa's Talking"""
        if not self.api_key:
            logger.warning("Africa's Talking not configured, skipping SMS")
            return False
            
        try:
            import requests
            
            headers = {
                'ApiKey': self.api_key,
                'Content-Type': 'application/x-www-form-urlencoded',
            }
            
            data = {
                'username': self.username,
                'to': self._format_phone(phone_number),
                'message': message[:1600],
            }
            
            if self.short_code:
                data['from'] = self.short_code
            
            response = requests.post(
                'https://api.africastalking.com/version1/messaging',
                headers=headers,
                data=data
            )
            
            if response.status_code == 201:
                logger.info(f"SMS sent to {phone_number}")
                return True
            else:
                logger.error(f"SMS failed: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send SMS: {e}")
            return False
    
    def _format_phone(self, phone: str) -> str:
        """Format phone number for Africa's Talking"""
        phone = ''.join(c for c in phone if c.isdigit())
        
        if not phone.startswith('27'):
            if phone.startswith('0'):
                phone = '27' + phone[1:]
            else:
                phone = '27' + phone
        
        return phone


class MockSMSProvider(SMSProvider):
    """Mock provider for development"""
    
    def __init__(self):
        self.sent_messages = []
        
    def send(self, phone_number: str, message: str) -> bool:
        """Log SMS instead of sending"""
        self.sent_messages.append({
            'to': phone_number,
            'message': message,
            'timestamp': timezone.now().isoformat()
        })
        logger.info(f"[MOCK SMS] To: {phone_number}, Message: {message[:50]}...")
        return True


def get_sms_provider():
    """Get configured SMS provider"""
    provider = getattr(settings, 'SMS_PROVIDER', 'mock')
    
    providers = {
        'twilio': TwilioSMSProvider,
        'africa_talking': AfricaTalkingSMSProvider,
        'mock': MockSMSProvider,
    }
    
    provider_class = providers.get(provider, MockSMSProvider)
    return provider_class()


# SMS Templates
SMS_TEMPLATES = {
    'issue_reported': """
KimConnect: Your report #{tracking_code} has been received.
Issue: {issue_type}
Location: {location}
We'll notify you when there's an update.
Track at: {track_url}
    """.strip(),
    
    'status_update': """
KimConnect: Update on report #{tracking_code}
Status: {new_status}
{message}
Track at: {track_url}
    """.strip(),
    
    'resolved': """
KimConnect: Great news! Report #{tracking_code} has been RESOLVED.
Issue: {issue_type}
Resolved by: {resolved_by}
Thank you for helping improve our community!
    """.strip(),
    
    'sla_warning': """
KimConnect: Report #{tracking_code} approaching deadline.
Issue: {issue_type}
Please expect resolution within {time_remaining}.
Track at: {track_url}
    """.strip(),
    
    'welcome': """
Welcome to KimConnect, {name}!
Report municipal issues in Kimberley easily.
Your account is ready. Start by reporting an issue at: {report_url}
Need help? Reply with HELP or call 053 830 6100.
    """.strip(),
}


def send_sms_notification(phone_number: str, template_name: str, context: dict) -> bool:
    """Send SMS notification using configured provider"""
    if template_name not in SMS_TEMPLATES:
        logger.error(f"Unknown SMS template: {template_name}")
        return False
    
    template = SMS_TEMPLATES[template_name]
    
    # Format template with context
    try:
        message = template.format(**context)
    except KeyError as e:
        logger.error(f"Missing context for SMS template: {e}")
        return False
    
    # Send via provider
    provider = get_sms_provider()
    return provider.send(phone_number, message)


def notify_issue_created(issue) -> dict:
    """Send notifications when issue is created"""
    from django.urls import reverse
    from django.contrib.sites.models import Site
    
    site = Site.objects.get_current()
    track_url = f"https://{site.domain}{reverse('tracking:issue_detail', args=[issue.id])}"
    
    context = {
        'tracking_code': issue.tracking_code,
        'issue_type': issue.get_issue_type_display(),
        'location': issue.area or 'Kimberley',
        'track_url': track_url,
    }
    
    results = {}
    
    # Send SMS if phone available
    if issue.reporter_phone:
        results['sms'] = send_sms_notification(
            issue.reporter_phone,
            'issue_reported',
            context
        )
    
    return results


def notify_status_change(issue, old_status, new_status, message='') -> dict:
    """Send notifications when issue status changes"""
    from django.urls import reverse
    from django.contrib.sites.models import Site
    
    site = Site.objects.get_current()
    track_url = f"https://{site.domain}{reverse('tracking:issue_detail', args=[issue.id])}"
    
    context = {
        'tracking_code': issue.tracking_code,
        'new_status': issue.get_status_display(),
        'message': message or 'Check the app for details.',
        'track_url': track_url,
    }
    
    results = {}
    
    if issue.reporter_phone:
        template = 'resolved' if new_status == 'resolved' else 'status_update'
        results['sms'] = send_sms_notification(
            issue.reporter_phone,
            template,
            context
        )
    
    return results
