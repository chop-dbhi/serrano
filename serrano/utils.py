from threading import Thread
from django.conf import settings
from django.core.mail import send_mail

def _send_mail(subject, message, sender, recipient_list, fail_silently):
    send_mail(subject, message, sender, recipient_list, fail_silently)

def email_users(users, subject, message, async=True, fail_silently=True):
    """Send email built from 'email_title' and 'email_body' to all 'users'

    'users' is an iterable collection of django.contrib.auth.models.User
    models. An email will be sent with the recipient list built from the 
    email_address properties on the users in 'users. Setting `async` to False
    will block while the email is being sent. If `fail_silently` is set to
    False, a SMTPException will be raised if there is an error sending the
    email.
    """
    email_addresses = [u.email for u in users if u.email]

    if async:
        Thread(target=_send_mail, args=(subject, message,
            settings.DEFAULT_FROM_EMAIL, email_addresses,
            fail_silently)).start()
    else:
        _send_mail(subject, message, settings.DEFAULT_FROM_EMAIL,
            email_addresses, fail_silently)
