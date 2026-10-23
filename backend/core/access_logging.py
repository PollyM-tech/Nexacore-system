"""Keep webhook bearer tokens and authentication headers out of Gunicorn access logs."""
import re
from gunicorn.glogging import Logger

CALLBACK = re.compile(r'(/hooks/stk/)[^/]+(/result/?)', re.IGNORECASE)


def safe_url(value):
    if not isinstance(value, str):
        return value
    value = CALLBACK.sub(r'\1[redacted]\2', value)
    # Access logs do not need query values; credentials must never be sent in URLs.
    return value.split('?', 1)[0]


class SafeAccessLogger(Logger):
    def atoms(self, resp, req, environ, request_time):
        clean = dict(environ)
        for key in ('RAW_URI', 'PATH_INFO', 'HTTP_REFERER'):
            if key in clean:
                clean[key] = safe_url(clean[key])
        clean['QUERY_STRING'] = ''
        for key in list(clean):
            if key.lower() in ('http_authorization', 'http_cookie', 'http_x_lintech_radius_key', 'http_x_api_key'):
                clean[key] = '[redacted]'
        atoms = super().atoms(resp, req, clean, request_time)
        for key in list(atoms):
            if key.startswith('{') and any(word in key.lower() for word in ('authorization', 'cookie', 'x-lintech-radius-key', 'x-api-key')):
                atoms[key] = '[redacted]'
        return atoms
