import ssl
from django.core.mail.backends.smtp import EmailBackend as SMTPBackend

class CustomEmailBackend(SMTPBackend):
    def open(self):
        """
        Override to disable SSL certificate verification.
        WARNING: Only use this in development!
        """
        if self.connection:
            return False
        
        try:
            # Create a new SSL context that doesn't verify certificates
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            # Initialize connection with our custom SSL context
            connection_params = {}
            if hasattr(self, 'timeout'):
                connection_params['timeout'] = self.timeout
            if hasattr(self, 'connection_timeout'):
                connection_params['timeout'] = self.connection_timeout
            if hasattr(self, 'local_hostname'):
                connection_params['local_hostname'] = self.local_hostname
                
            connection = self.connection_class(
                self.host, self.port, **connection_params
            )
            
            # Apply TLS with our custom SSL context
            connection.starttls(context=ssl_context)
            
            # Authenticate if credentials were provided
            if self.username and self.password:
                connection.login(self.username, self.password)
                
            return connection
        except Exception as e:
            if not self.fail_silently:
                raise e
            return None
