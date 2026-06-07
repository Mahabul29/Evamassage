import re

class SecurityMiddleware:
    @staticmethod
    def sanitize_input(text):
        if not text:
            return text
        text = re.sub(r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>', '', text, flags=re.IGNORECASE)
        return text

security = SecurityMiddleware()
