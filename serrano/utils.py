from django.conf import settings
from django.core.mail import send_mail

def email_users(users, email_title, email_body):
    """Send email built from 'email_title' and 'email_body' to all 'users'

    'users' is an iterable collection of django.contrib.auth.models.User
    models. An email will be sent with the recipient list built from the 
    email_address properties on the users in 'users.
    """
    email_addresses = [u.email for u in users if u.email]
    send_mail(email_title, email_body, settings.DEFAULT_FROM_EMAIL, 
        email_addresses, fail_silently=True)
