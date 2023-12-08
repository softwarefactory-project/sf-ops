#!/bin/env python3

import argparse
import base64
from functools import partial
import hashlib
import http.server as httpserver
import logging
import os
import re
import requests
import sys
from threading import Thread
import time
from urllib.parse import urlparse, urljoin, parse_qs, urlencode
import webbrowser
from zuulclient.api import ZuulRESTClient


log = logging.getLogger("zc-web-auth")


STATIC_SUCCESS = """
<html>
<h1>Success !</h1>
<br />
You can safely close this window.
</html>""".encode('utf-8')


UPSTREAM = ["sfio", "rdo"]
DOWNSTREAM = ["downstream", "sfhosted", "upshift"]


def get_zuul_client(zuul):
    if zuul in UPSTREAM:
        return (ZuulRESTClient(
            "https://softwarefactory-project.io/zuul/",
            verify=True), True)
    elif zuul in DOWNSTREAM:
        import urllib3
        urllib3.disable_warnings()
        return (ZuulRESTClient(
            "https://sf.hosted.upshift.rdu2.redhat.com/zuul/",
            verify=False), False)
    else:
        log.error("zuul must be one of: %s" % ', '.join(UPSTREAM + DOWNSTREAM))
        sys.exit(1)


def get_oidc_config(authority, verify=True):
    _authority = authority
    if not _authority.endswith('/'):
        _authority += ('/')
    oidc_config = requests.get(
        _authority + '.well-known/openid-configuration',
        verify=verify
    )
    oidc_config.raise_for_status()
    return oidc_config.json()


def do_nothing(*args, **kwargs):
    return


class AuthServer(httpserver.BaseHTTPRequestHandler):

    def __init__(
        self, request, client_address, server,
        client_ID, openID_config, port,
        verify, callback_func, logger,
        code_verifier=None
    ):
        self.client_id = client_ID
        self.openID_config = openID_config
        self.web_port = port
        self.verify = verify
        self.callback_func = callback_func
        self.logger = logger
        self.code_verifier = code_verifier
        if self.code_verifier is None:
            self.code_verifier = generate_code_verifier()
        super().__init__(request, client_address, server)

    def log_message(self, format, *args):
        return

    def response_start(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_GET(self):
        params = parse_qs(urlparse(self.path).query)
        self.response_start()
        if 'code' in params:
            data = {
                'grant_type': 'authorization_code',
                'code': params['code'],
                'client_id': self.client_id,
                'redirect_uri': 'http://localhost:%i/' % self.web_port,
                'code_verifier': self.code_verifier,
            }
            self.logger.debug("Exchanging code for access token:")
            self.logger.debug("POST %s?%s" % (
                self.openID_config['token_endpoint'],
                urlencode(data)
            ))
            token_query = requests.post(
                self.openID_config['token_endpoint'],
                data=data,
                verify=self.verify
            )
            tokens = token_query.json()
            if 'access_token' in tokens:
                self.wfile.write(STATIC_SUCCESS)
                self.logger.debug("Received tokens: %s" % tokens)
                self.callback_func(access_token=tokens['access_token'])
            else:
                self.wfile.write(
                    ('The identity provider could not issue an access token. '
                     'The IdP returned: {}'.format(token_query.text)
                    ).encode('utf-8'))
                self.callback_func(failure=True)
        else:
            self.wfile.write(
                ('You are here by mistake, or because your identity '
                 'provider did not return an authorization code. '
                 'Returned parameters: {}'
                ).format(params).encode('utf-8')
            )
            self.callback_func(failure=True)


def generate_code_verifier():
    code_verifier = base64.urlsafe_b64encode(os.urandom(40)).decode('utf-8')
    code_verifier = re.sub('[^0-9a-zA-Z]+', '', code_verifier)
    return code_verifier


def generate_code_challenge(code_verifier):
    code_challenge = hashlib.sha256(code_verifier.encode('utf-8')).digest()
    code_challenge = base64.urlsafe_b64encode(code_challenge).decode('utf-8')
    # remove padding
    code_challenge = code_challenge.replace('=', '')
    return code_challenge


def run_server(
    client_id, openID_config,
    port, verify, code_verifier, logger, callback_func=do_nothing
):
    address = ('localhost', port)
    handler_class = partial(
        AuthServer,
        client_ID=client_id,
        openID_config=openID_config,
        verify=verify,
        port=port,
        callback_func=callback_func,
        logger=logger,
        code_verifier=code_verifier)
    httpd = httpserver.HTTPServer(address, handler_class)

    def serve_forever():
        httpd.server_activate()
        with httpd:
            httpd.serve_forever()

    thread = Thread(target=serve_forever)
    thread.daemon = True
    thread.start()
    return httpd, thread


class Semaphore(object):
    wait = True


S = Semaphore()


def start_web_auth(
    client_id, scope, openID_config, logger,
    port=8085, verify=True):

    code_verifier = generate_code_verifier()
    logger.debug("PKCE code verifier: %s" % code_verifier)

    def callback(*args, **kwargs):
        if 'access_token' in kwargs:
            print(kwargs['access_token'])
            S.wait = False
        else:
            raise Exception(
                'Authentication process failed: access token '
                'missing from Identity Provider\'s response.')

    httpd, _ = run_server(
        client_id, openID_config, port, verify,
        code_verifier, logger, callback
    )

    code_challenge = generate_code_challenge(code_verifier)

    base_auth_url = openID_config['authorization_endpoint']
    payload = {
        'client_id': client_id,
        'redirect_uri': 'http://localhost:%i/' % port,
        'response_type': 'code',
        'scope': scope,
        'code_challenge': code_challenge,
        'code_challenge_method': 'S256',
    }
    auth_url = "%s?%s" % (base_auth_url, urlencode(payload))
    logger.debug("Opening %s" % auth_url)
    webbrowser.open_new(auth_url)
    while S.wait:
        time.sleep(0.1)
    httpd.server_close()


def main():
    parser = argparse.ArgumentParser(
        usage="""
zuul-client SSO auth helper

Run this script to generate an auth token to use with zuul-client.
The script will open a web browser window from which you can perform
the regular authentication flow with SSO.

TCP port 8085 needs to be available on your system and obviously, you
need to be able to open a web browser.

Recommended usage:

TOKEN=$(zc-web-auth.py --zuul downstream --tenant tripleo-ci-internal)
zuulclient --auth-token=$TOKEN ...
""")
    parser.add_argument('--zuul', metavar='ZUUL_INSTANCE',
                        dest='zuul',
                        choices = UPSTREAM + DOWNSTREAM,
                        default='sfio',
                        required=False,
                        help='the Zuul instance on which to authenticate. If you choose "rdo" the tenant will automatically be set.' +\
                             ' Allowed values are %s (ie https://softwarefactory-project.io);' % ', '.join(UPSTREAM) +\
                             ' and %s (ie https://sf.hosted.upshift.rdu2.redhat.com).' % ', '.join(DOWNSTREAM) +\
                             ' Defaults to "sfio".')
    parser.add_argument('--tenant', metavar='TENANT',
                        dest='tenant',
                        default='local',
                        required=False,
                        help='The tenant against which to authenticate. Mandatory unless chosen zuul instance is "rdo".')
    args = parser.parse_args()
    if args.zuul == "rdo":
        log.debug("Overwriting tenant argument to match rdo")
        args.tenant = "rdoproject.org"
    client, verify = get_zuul_client(args.zuul)
    try:
        tenant_info = client.tenant_info(args.tenant)
    # current version of zuulclient on PyPI is very old, tenant_info() might not be available
    except Exception:
        req = client.session.get(urljoin(client.base_url, 'tenant/%s/info' % args.tenant))
        tenant_info = req.json().get('info', {})
    auth_config = tenant_info["capabilities"].get("auth")
    realm = auth_config.get('default_realm')
    realm_config = auth_config['realms'][realm]
    authority = realm_config["authority"]
    client_id = realm_config["client_id"]
    scope = realm_config["scope"]
    oidc_config = get_oidc_config(authority, verify)
    start_web_auth(client_id, scope, oidc_config, port=8085, verify=verify, logger=log)

if __name__ == '__main__':
    main()