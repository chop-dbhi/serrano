from django.core.urlresolvers import reverse
from urllib import unquote


def _get_link(name, link, data=None):
    """
    Creates a link header field based on the supplied name, link, and data.

    If the data is empty, then a link header field with a rel tag and link
    value are generated. Otherwise, data is considered to contain keys and
    values representing the available link header fields as noted in the RFC
    here:

        https://tools.ietf.org/html/rfc5988#section-5

    When data is present, its content will be added after the link value and
    rel fields.
    """
    if data is None:
        return '<{0}>; rel="{1}"'.format(link, name)

    header_data = []

    for key, value in data.items():
        header_data.append('{0}="{1}"'.format(key, value))

    if header_data:
        header_data = '; {0}'.format('; '.join(header_data))
    else:
        header_data = ''

    return '<{0}>; rel="{1}"{2}'.format(link, name, header_data)


def _get_links(data):
    """
    Returns a comma separated list of link header fields.

    For more information on how the individual fields are generated, see the
    _get_link(...) method above.
    """
    links = []

    for name, value in data.items():
        if isinstance(value, basestring):
            links.append(_get_link(name, value))
        else:
            links.append(_get_link(name, value['link'], value['data']))

    if links:
        return ', '.join(links)

    return links


def reverse_tmpl(uri, name, params):
    """
    Returns an unquoted uri containing the reverse name with param replacement.

    This methods does a number of things. If there were no params, all that
    would happend would be that the name would be reversed, that reversed
    name would be passed to the supplied uri method, and that unquoted uri
    would be returned. When params are present, we will modify the reversed
    name.

    Params should be a dictionary in the following form:

        {
            url_param: (type, alias),
            ...
        }

    So, let's consider the url for retrieving a single view:

        url(r'^(?P<pk>\d+)/$', single_resource, name='single')

    Then we would constructs params as:

        {
            'pk': (int, 'id')
        }

    Which instructs this method that the pk url param is an integer and should
    be replaced in the final uri with `{id}`. The types supported by this
    method are:

        (complex, float, int, long, str)

    Which should cover all the cases we could possibly see in the URL. Also,
    these happen to be all the cases we can safely convert an int to. This is
    important because we use integers as placeholders when reversing the URL
    and then we replace those integers with the aliases after all the
    reversals are done. As noted below, this has the limitation of only
    supporting 10 params. The reason for this limitation is in the replacement.
    Let's say we had 11 params then the 11th param would take the placeholder
    10. When we go to replace, we might try to replace 0 and 1 before 10 which
    means that the 1 and 0 in 10 might be replaced before 10 itself is replaced
    which would obviously return a malformed uri. This is acceptable in our
    case as we don't have any urls with more than 2 params so until there is
    a strong use case for supporting 11+ url params, this should suffice.

    The unquoting occurs becuase we don't want %7B and %7D for { and }
    respectively in the returned url. This will occur because the replacement
    is occuring before the call to uri which will quote those characters. If
    for nothing else, this increases readability of the URLs and makes the
    URLs consistent for the client.
    """

    kwargs = {}
    variables = {}
    supported_types = (complex, float, int, long, str)

    # NOTE: It is known that this method will only support 10 replacements
    # for values [0-9] before there would be "collisions" when replacing but
    # we have now use cases for URLs with 10 or more url parameters so this
    # should be safe for our uses and we can adapt this should that case ever
    # come to exist.
    param_num = 0
    for key, type_alias in params.items():
        type = type_alias[0]
        alias = type_alias[1]

        if type not in supported_types:
            raise ValueError(
                'Cannot reverse template with type {0}. The supported types '
                'are {1}.'.format(type, supported_types))

        value = type(param_num)
        variables[str(value)] = '{{{0}}}'.format(alias)
        kwargs[key] = value

        param_num += 1

    url = reverse(name, kwargs=kwargs)
    for val, var in variables.items():
        url = url.replace(val, var)

    return unquote(uri(url))


def patch_response(request, response, links, link_templates):
    """
    Sets the Link and Link-Template header fields on the response.

    These fields will only be set if the supplied link and link_templates are
    non-empty and those header fields are not already set on the supplied
    response object.
    """

    if 'Link' not in response and links:
        response['Link'] = _get_links(links)

    if 'Link-Template' not in response and link_templates:
        response['Link-Template'] = _get_links(link_templates)

    return response
