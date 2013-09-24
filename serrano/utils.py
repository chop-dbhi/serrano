from threading import Thread
from django.conf import settings
from django.core import mail


def _send_mail(subject, message, sender, recipient_list, fail_silently):
    mail.send_mail(subject, message, sender, recipient_list, fail_silently)


def send_mail(emails, subject, message, async=True, fail_silently=True):
    """Send email built from 'email_title' and 'email_body' to all 'emails'

    'emails' is an iterable collection of email addresses to notify. Setting
    `async` to False will block while the email is being sent. If
    `fail_silently` is set to False, a SMTPException will be raised if there
    is an error sending the email.

    NOTE: This method makes NO effort to validate the emails before sending.
    To avoid any issues while sending emails, validate before calling this
    method.
    """
    if async:
        # We pass a copy of the list of emails to the thread target to avoid it
        # going out of scope within the thread target. This was happening when
        # obtaining the the list of emails from a QuerySet of Django User
        # objects. It's easier to pass a copy here than worrying about it
        # when calling this utility method.
        Thread(target=_send_mail,
               args=(subject, message, settings.DEFAULT_FROM_EMAIL,
                     list(emails), fail_silently)).start()
    else:
        _send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, emails,
                   fail_silently)
