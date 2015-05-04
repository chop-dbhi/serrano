from threading import Thread
from django.conf import settings
from django.core import mail
from avocado.export import HTMLExporter, registry as exporters
from avocado.query import pipeline, utils as query_utils


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


def get_result_rows(context, view, limit, tree, processor_name, page,
                    stop_page, query_name, reader, export_type):
    """
    TODO: Doctstring
    """
    offset = None

    if page:
        page = int(page)

        # Pages are 1-based.
        if page < 1:
            raise ValueError('Page must be greater than or equal to 1.')

        # Change to 0-base for calculating offset.
        offset = limit * (page - 1)

        if stop_page:
            stop_page = int(stop_page)

            # Cannot have a lower index stop page than start page.
            if stop_page < page:
                raise ValueError(
                    'Stop page must be greater than or equal to start page.')

            # 4...5 means 4 and 5, not everything up to 5 like with
            # list slices, so 4...4 is equivalent to just 4
            if stop_page > page:
                limit = limit * stop_page
    else:
        # When no page or range is specified, the limit does not apply.
        limit = None

    QueryProcessor = pipeline.query_processors[processor_name]
    processor = QueryProcessor(context=context, view=view, tree=tree)
    queryset = processor.get_queryset()

    # Isolate this query to a named connection. This will cancel an
    # outstanding queries of the same name if one is present.
    query_utils.cancel_query(query_name)
    queryset = query_utils.isolate_queryset(query_name, queryset)

    # 0 limit means all for pagination, however the read method requires
    # an explicit limit of None
    limit = limit or None

    # We use HTMLExporter in Serrano but Avocado has it disabled. Until it
    # is enabled in Avocado, we can reference the HTMLExporter directly here.
    if export_type.lower() == 'html':
        exporter = processor.get_exporter(HTMLExporter)
    else:
        exporter = processor.get_exporter(exporters[export_type])

    # This is an optimization when concepts are selected for ordering
    # only. There is no guarantee to how many rows are required to get
    # the desired `limit` of rows, so the query is unbounded. If all
    # ordering facets are visible, the limit and offset can be pushed
    # down to the query.
    order_only = lambda f: not f.get('visible', True)
    view_node = view.parse()

    if filter(order_only, view_node.facets):
        iterable = processor.get_iterable(queryset=queryset)
        rows = exporter.manual_read(iterable,
                                    offset=offset,
                                    limit=limit)
    else:
        iterable = processor.get_iterable(queryset=queryset,
                                          limit=limit,
                                          offset=offset)
        iterable = processor.get_iterable(queryset=queryset,
                                          limit=limit,
                                          offset=offset)
        method = exporter.reader(reader)
        rows = method(iterable)

    options = {
        'exporter': exporter,
        'queryset': queryset,
        'offset': offset,
        'limit': limit,
        'page': page,
        'stop_page': stop_page,
    }

    return rows, options
