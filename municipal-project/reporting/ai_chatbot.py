"""
AI Chatbot Integration for KimConnect
Supports OpenAI GPT and local AI models
"""

import os
import json
import logging
from django.conf import settings
from typing import Optional

logger = logging.getLogger(__name__)


class AIChatbot:
    """Base class for AI chatbot implementations"""
    
    def __init__(self):
        self.system_prompt = self._get_system_prompt()
        
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the chatbot"""
        return """You are KimConnect, an AI assistant for Sol Plaatje Municipality's citizen service platform in Kimberley, Northern Cape, South Africa.

Your role is to help citizens:
1. Report municipal issues (water, electricity, potholes, sanitation, roads)
2. Track their reported issues using tracking codes
3. Understand municipal services and hours
4. Navigate the KimConnect platform
5. Get emergency contact information

Key Information:
- Municipal Offices: Mon-Fri 08:00-16:30
- Emergency Water: 053 830 6100
- Emergency Electricity: 053 830 6500
- Website: www.solplaatje.gov.za
- Location: Kimberley, Northern Cape

Always be:
- Helpful and friendly
- Concise (under 3 sentences for simple queries)
- Clear about what the user should do next
- Empathetic about municipal service issues

If asked about specific issues or complex problems, guide them to submit a formal report through the app or contact the municipality directly.

Never make up information. If you don't know something, say so and suggest contacting the municipality directly."""
    
    def generate_response(self, user_message: str, context: Optional[dict] = None) -> dict:
        """Generate AI response to user message"""
        raise NotImplementedError
    
    def analyze_intent(self, message: str) -> str:
        """Analyze user intent from message"""
        message_lower = message.lower()
        
        intents = {
            'report_issue': ['report', 'problem', 'issue', 'pothole', 'leak', 'no water', 'no electricity', 'report an'],
            'track_issue': ['track', 'status', 'where is', 'when will', 'update on', 'tracking code', 'my report'],
            'municipal_hours': ['hours', 'open', 'close', 'when open', 'working hours', 'time'],
            'emergency': ['emergency', 'urgent', 'danger', 'safety', 'quick'],
            'location': ['where', 'address', 'location', 'find office', 'come to'],
            'complaint': ['complaint', 'unhappy', 'frustrated', 'still broken', 'not fixed', 'worst'],
            'greeting': ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening'],
            'thanks': ['thank', 'thanks', 'appreciate', 'helpful'],
        }
        
        for intent, keywords in intents.items():
            if any(keyword in message_lower for keyword in keywords):
                return intent
        
        return 'general'
    
    def get_quick_response(self, intent: str) -> str:
        """Get quick response for common intents"""
        responses = {
            'report_issue': "I'd be happy to help you report an issue! Click the 'Report Issue' button or tell me what type of problem you're experiencing (water, electricity, pothole, etc.) and I'll guide you through the process.",
            
            'track_issue': "To track your issue, I need your tracking code (starts with 'KC-'). Once you provide it, I can check the current status. You can also track directly at /track/",
            
            'municipal_hours': "Sol Plaatje Municipality offices are open Monday to Friday, 08:00 to 16:30. For emergencies outside these hours, call our 24/7 hotline at 053 830 6100.",
            
            'emergency': "For urgent municipal emergencies like major water leaks or electrical hazards, please call immediately:\n• Water: 053 830 6100\n• Electricity: 053 830 6500\n• Police: 10111",
            
            'location': "Sol Plaatje Municipality is located at:\n📍 Civic Centre\n💼 114 Bultfontein St\n🏙️ Kimberley, 8301\n\nYou can also visit during office hours (Mon-Fri, 08:00-16:30).",
            
            'complaint': "I understand your frustration. If an issue hasn't been resolved, please provide your tracking code and I'll escalate it. You can also call the municipality directly at 053 830 6100 to lodge a formal complaint.",
            
            'greeting': "Hello! 👋 I'm KimConnect, here to help you with municipal services in Kimberley. How can I assist you today?",
            
            'thanks': "You're welcome! 😊 Is there anything else I can help you with?",
        }
        
        return responses.get(intent, "I'm here to help! Could you tell me more about what you need assistance with?")


class OpenAIChatbot(AIChatbot):
    """OpenAI GPT-powered chatbot"""
    
    def __init__(self):
        super().__init__()
        self.api_key = getattr(settings, 'OPENAI_API_KEY', '')
        self.model = getattr(settings, 'OPENAI_MODEL', 'gpt-3.5-turbo')
        
    def generate_response(self, user_message: str, context: Optional[dict] = None) -> dict:
        """Generate response using OpenAI API"""
        if not self.api_key:
            # Fallback to rule-based response
            intent = self.analyze_intent(user_message)
            return {
                'response': self.get_quick_response(intent),
                'intent': intent,
                'source': 'rule_based',
                'confidence': 0.8
            }
        
        try:
            import openai
            
            messages = [
                {"role": "system", "content": self.system_prompt},
            ]
            
            # Add context if available
            if context:
                context_str = json.dumps(context, indent=2)
                messages.append({
                    "role": "system", 
                    "content": f"Context about current page/situation:\n{context_str}"
                })
            
            # Add conversation history if available
            if context and 'history' in context:
                for msg in context['history'][-5:]:  # Last 5 messages
                    messages.append(msg)
            
            messages.append({"role": "user", "content": user_message})
            
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=messages,
                max_tokens=300,
                temperature=0.7,
                presence_penalty=0.1,
                frequency_penalty=0.1
            )
            
            intent = self.analyze_intent(user_message)
            
            return {
                'response': response.choices[0].message.content,
                'intent': intent,
                'source': 'openai',
                'usage': {
                    'tokens': response.usage.total_tokens
                }
            }
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            intent = self.analyze_intent(user_message)
            return {
                'response': self.get_quick_response(intent),
                'intent': intent,
                'source': 'rule_based',
                'error': str(e)
            }


class ClaudeChatbot(AIChatbot):
    """Anthropic Claude-powered chatbot"""
    
    def __init__(self):
        super().__init__()
        self.api_key = getattr(settings, 'ANTHROPIC_API_KEY', '')
        self.model = getattr(settings, 'CLAUDE_MODEL', 'claude-2')
        
    def generate_response(self, user_message: str, context: Optional[dict] = None) -> dict:
        """Generate response using Claude API"""
        if not self.api_key:
            intent = self.analyze_intent(user_message)
            return {
                'response': self.get_quick_response(intent),
                'intent': intent,
                'source': 'rule_based'
            }
        
        try:
            import anthropic
            
            client = anthropic.Anthropic(api_key=self.api_key)
            
            prompt = f"{self.system_prompt}\n\nHuman: {user_message}\n\nAssistant:"
            
            if context:
                prompt = f"Context: {json.dumps(context)}\n\n{prompt}"
            
            response = client.completions.create(
                model=self.model,
                prompt=prompt,
                max_tokens_to_sample=300,
                temperature=0.7
            )
            
            intent = self.analyze_intent(user_message)
            
            return {
                'response': response.completion,
                'intent': intent,
                'source': 'claude'
            }
            
        except Exception as e:
            logger.error(f"Claude API error: {e}")
            intent = self.analyze_intent(user_message)
            return {
                'response': self.get_quick_response(intent),
                'intent': intent,
                'source': 'rule_based'
            }


class LocalAIChatbot(AIChatbot):
    """Local AI model chatbot (for offline/privacy)"""
    
    def __init__(self):
        super().__init__()
        self.endpoint = getattr(settings, 'LOCAL_AI_ENDPOINT', 'http://localhost:8080/v1/completions')
        self.model = getattr(settings, 'LOCAL_AI_MODEL', 'local-model')
        
    def generate_response(self, user_message: str, context: Optional[dict] = None) -> dict:
        """Generate response using local AI model"""
        intent = self.analyze_intent(user_message)
        
        # Try local endpoint
        try:
            import requests
            
            prompt = f"{self.system_prompt}\n\nUser: {user_message}\n\nAssistant:"
            
            response = requests.post(
                self.endpoint,
                json={
                    'prompt': prompt,
                    'max_tokens': 300,
                    'temperature': 0.7,
                    'model': self.model
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'response': data.get('choices', [{}])[0].get('text', self.get_quick_response(intent)),
                    'intent': intent,
                    'source': 'local_ai'
                }
                
        except Exception as e:
            logger.warning(f"Local AI unavailable: {e}")
        
        # Fallback to rule-based
        return {
            'response': self.get_quick_response(intent),
            'intent': intent,
            'source': 'rule_based'
        }


def get_ai_chatbot():
    """Get configured AI chatbot"""
    provider = getattr(settings, 'AI_CHATBOT_PROVIDER', 'rule_based')
    
    providers = {
        'openai': OpenAIChatbot,
        'claude': ClaudeChatbot,
        'local': LocalAIChatbot,
        'rule_based': AIChatbot,
    }
    
    chatbot_class = providers.get(provider, AIChatbot)
    return chatbot_class()


def chat(user_message: str, context: Optional[dict] = None) -> dict:
    """Main chat function"""
    chatbot = get_ai_chatbot()
    return chatbot.generate_response(user_message, context)


# Quick action handlers
QUICK_ACTIONS = {
    'water_leak': {
        'response': "To report a water leak:\n1. Go to Report Issue\n2. Select 'Water' as issue type\n3. Add your location\n4. Upload a photo if possible\n5. Submit\n\nFor major leaks, call 053 830 6100 immediately.",
        'action': 'open_report_form',
        'params': {'issue_type': 'water'}
    },
    'pothole': {
        'response': "To report a pothole:\n1. Go to Report Issue\n2. Select 'Potholes/Roads'\n3. Pin the exact location\n4. Add photo if safe\n5. Submit\n\nFor dangerous potholes on major roads, call 053 830 6100.",
        'action': 'open_report_form',
        'params': {'issue_type': 'roads'}
    },
    'electricity': {
        'response': "For electricity issues:\n• No power: Check if it's a planned outage at municipal website\n• Emergency/unsafe: Call 053 830 6500 immediately\n• Report outage: Use the Report form\n\nFor life-threatening electrical situations, call 10111.",
        'action': 'open_report_form',
        'params': {'issue_type': 'electricity'}
    },
    'track': {
        'response': "Enter your tracking code (format: KC-XXXXXX) to check status. You can find it in:\n• SMS confirmation\n• Email confirmation\n• The tracking page",
        'action': 'open_track_form'
    },
    'hours': {
        'response': "📍 Sol Plaatje Municipality\n\n🕐 Office Hours:\nMon-Fri: 08:00 - 16:30\n\n📞 Emergency Hotline: 24/7\nWater: 053 830 6100\nElectricity: 053 830 6500",
        'action': None
    },
}


def handle_quick_action(action: str) -> dict:
    """Handle quick action buttons"""
    return QUICK_ACTIONS.get(action, {
        'response': "I'm not sure about that. Could you describe what you need?",
        'action': None
    })
