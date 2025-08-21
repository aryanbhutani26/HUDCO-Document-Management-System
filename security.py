# security.py
import re
import html

class SecurityManager:
    
    @staticmethod
    def sanitize_input(text):
        """Sanitize user input to prevent prompt injection"""
        # Remove HTML tags
        text = html.escape(text)
        
        # Remove potential instruction keywords
        dangerous_patterns = [
            r'ignore\s+previous\s+instructions',
            r'system\s*:',
            r'assistant\s*:',
            r'<\s*/?system\s*>',
            r'<\s*/?assistant\s*>'
        ]
        
        for pattern in dangerous_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        return text.strip()
    
    @staticmethod
    def validate_file_type(filename):
        """Validate uploaded file type"""
        allowed_extensions = {'.pdf'}
        return any(filename.lower().endswith(ext) for ext in allowed_extensions)
