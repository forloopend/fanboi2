import hashlib
import requests
import socket
from IPy import IP
from .models import redis_conn
from .version import __VERSION__


def serialize_request(request):
    """Serialize :class:`pyramid.util.Request` into a :type:`dict`."""

    if isinstance(request, dict):
        return request

    return {
        'application_url': request.application_url,
        'remote_addr': request.remote_addr,
        'user_agent': request.user_agent,
        'referrer': request.referrer,
        'url': request.url,
    }


class Dnsbl(object) :
    """Utility class for checking IP address against DNSBL providers."""

    def __init__(self):
        self.providers = []

    def configure_providers(self, providers):
        self.providers = providers

    def listed(self, ip_address):
        """Returns :type:`True` if the given IP address is listed in the
        DNSBL providers. Returns :type:`False` if not listed or no DNSBL
        providers present.
        """
        if self.providers:
            for provider in self.providers:
                try:
                    check = '.'.join(reversed(ip_address.split('.')))
                    res = socket.gethostbyname("%s.%s." % (check, provider))
                    if IP(res).make_net('255.0.0.0') == IP('127.0.0.0/8'):
                        return True
                except (socket.gaierror, ValueError):
                    continue
        return False


dnsbl = Dnsbl()


class Akismet(object):
    """Basic integration between Pyramid and Akismet."""

    def __init__(self):
        self.key = None

    def configure_key(self, key):
        self.key = key

    def _api_post(self, name, data=None):
        return requests.post(
            'https://%s.rest.akismet.com/1.1/%s' % (self.key, name),
            headers={'User-Agent': "Fanboi2/%s | Akismet/0.1" % __VERSION__},
            data=data,
            timeout=2)

    def spam(self, request, message):
        """Returns :type:`True` if `message` is spam. Always returns
        :type:`False` if Akismet key is not set or the request to Akismet
        was timed out.
        """
        if self.key:
            request = serialize_request(request)
            try:
                return self._api_post('comment-check', data={
                    'blog': request['application_url'],
                    'user_ip': request['remote_addr'],
                    'user_agent': request['user_agent'],
                    'referrer': request['referrer'],
                    'permalink': request['url'],
                    'comment_type': 'comment',
                    'comment_content': message,
                }).content == b'true'
            except requests.Timeout:
                return False
        return False


class RateLimiter(object):
    """Rate limit to throttle content posting to every specific seconds."""

    def __init__(self, request, namespace=None):
        request = serialize_request(request)
        self.key = "rate:%s:%s" % (
            namespace,
            hashlib.md5(request['remote_addr'].encode('utf8')).hexdigest(),
        )

    def limit(self, seconds=10):
        """Mark user as rate limited for `seconds`."""
        redis_conn.set(self.key, 1)
        redis_conn.expire(self.key, seconds)

    def limited(self):
        """Returns true if content should be limited from posting."""
        return redis_conn.exists(self.key)

    def timeleft(self):
        """Returns seconds left until user is no longer throttled."""
        return redis_conn.ttl(self.key)


akismet = Akismet()
