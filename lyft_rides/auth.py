# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""An internal module to handle OAuth 2.0 Authorization.
There are three ways you may obtain an access token:
    - Authorization Code Grant (3-Legged Flow)
    - Client Credentials Grant (2-Legged Flow)
Each OAuth 2.0 grant uses your app credentials to start an
authorization process with Lyft. Upon successful authorization,
a Session is created, which stores the OAuth 2.0 credentials.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from collections import OrderedDict
from random import SystemRandom
from requests import codes
from requests import post
from requests.auth import HTTPBasicAuth
from string import ascii_letters
from string import digits

try:
    from urllib.parse import parse_qs
    from urllib.parse import urlparse
except ImportError:
    from urlparse import parse_qs
    from urlparse import urlparse

from lyft_rides.errors import ClientError
from lyft_rides.errors import LyftIllegalState
from lyft_rides.session import OAuth2Credential
from lyft_rides.session import Session
from lyft_rides.utils import auth
from lyft_rides.utils.request import build_url


class OAuth2(object):
    """The parent class for all OAuth 2.0 grant types."""

    def __init__(self, client_id, scopes):
        """Initialize OAuth 2.0 Class.
        Parameters
            client_id (str)
                Your app's Client ID.
            scopes (set)
                Set of permission scopes to request.
                (e.g. {'profile', 'rides.request'})
        """
        self.client_id = client_id
        self.scopes = scopes

    def _build_authorization_request_url(
        self,
        response_type,
        state=None
    ):
        """Form URL to request an auth code or access token.
        Parameters
            response_type (str)
                Only 'code' (Authorization Code Grant) supported at this time
            state (str)
                Optional CSRF State token to send to server.
        Returns
            (str)
                The fully constructed authorization request URL.
        Raises
            LyftIllegalState (ApiError)
                Raised if response_type parameter is invalid.
        """
        if response_type not in auth.VALID_RESPONSE_TYPES:
            message = '{} is not a valid response type.'
            raise LyftIllegalState(message.format(response_type))

        args = OrderedDict([
            ('scope', ' '.join(self.scopes)),
            ('state', state),
            ('response_type', response_type),
            ('client_id', self.client_id),
        ])

        return build_url(auth.SERVER_HOST, auth.AUTHORIZE_PATH, args)

    def _extract_query(self, redirect_url):
        """Extract query parameters from a url.
        Parameters
            redirect_url (str)
                The full URL that the Lyft server redirected to after
                the user authorized your app.
        Returns
            (dict)
                A dictionary of query parameters.
        """
        qs = urlparse(redirect_url)

        # redirect_urls return data after query identifier (?)
        qs = qs.query

        query_params = parse_qs(qs)
        query_params = {qp: query_params[qp][0] for qp in query_params}

        return query_params


class AuthorizationCodeGrant(OAuth2):
    """Class for Authorization Code Grant type.
    The authorization code grant type is used to obtain both access
    tokens and refresh tokens and is optimized for confidential clients.
    It involves a two-step authorization process. The first step is having
    the user authorize your app. The second involves getting an OAuth 2.0
    access token from Lyft.
    """

    def __init__(
        self,
        client_id,
        client_secret,
        scopes,
        is_sandbox_mode=True,
        state_token=None,
    ):
        """Initialize AuthorizationCodeGrant Class.
        Parameters
            client_id (str)
                Your app's Client ID.
            client_secret (str)
                Your app's Client Secret.
            scopes (set)
                Set of permission scopes to request.
                (e.g. {'profile', 'rides.request'}) Keep this list minimal so
                users feel safe granting your app access to their information.
            is_sandbox_mode (bool)
                Optional. Set to False if your code is in production.
            state_token (str)
                The CSRF State Token used to create an authorization.
        """
        super(AuthorizationCodeGrant, self).__init__(client_id, scopes)
        self.client_secret = "-".join([auth.SANDBOX_MODE_PREFIX, client_secret]) if is_sandbox_mode else client_secret
        if state_token is not None:
            self.state_token = state_token
        else:
            self.state_token = self._generate_state_token()

    def _generate_state_token(self, length=32):
        """Generate CSRF State Token.
        CSRF State Tokens are passed as a parameter in the authorization
        URL and are checked when receiving responses from the Lyft Auth
        server to prevent request forgery.
        """
        choices = ascii_letters + digits
        return ''.join(SystemRandom().choice(choices) for _ in range(length))

    def get_authorization_url(self):
        """Start the Authorization Code Grant process.
        This function starts the OAuth 2.0 authorization process and builds an
        authorization URL. You should redirect your user to this URL, where
        they can grant your application access to their Lyft account.
        Returns
            (str)
                The fully constructed authorization request URL.
                Tell the user to visit this URL and approve your app.
        """
        return self._build_authorization_request_url(
            response_type=auth.CODE_RESPONSE_TYPE,
            state=self.state_token,
        )

    def _verify_query(self, query_params):
        """Verify response from the Lyft Auth server.
        Parameters
            query_params (dict)
                Dictionary of query parameters attached to your redirect URL
                after user approved your app and was redirected.
        Returns
            authorization_code (str)
                Code received when user grants your app access. Use this code
                to request an access token.
        Raises
            LyftIllegalState (ApiError)
                Thrown if the redirect URL was missing parameters or if the
                given parameters were not valid.
        """
        error_message = None

        # Check CSRF State Token against returned state token from GET request
        received_state_token = query_params.get('state')
        if received_state_token is None:
            error_message = 'Bad Request. Missing state parameter.'
            raise LyftIllegalState(error_message)

        if self.state_token is None:
            error_message = 'Missing CSRF State Token in session.'
            raise LyftIllegalState(error_message)

        if self.state_token != received_state_token:
            error_message = 'CSRF Error. Expected {}, got {}'
            error_message = error_message.format(
                self.state_token,
                received_state_token,
            )
            raise LyftIllegalState(error_message)

        # Verify either 'code' or 'error' parameter exists
        error = query_params.get('error')
        authorization_code = query_params.get(auth.CODE_RESPONSE_TYPE)

        if error and authorization_code:
            error_message = (
                'Code and Error query params code and error '
                'can not both be set.'
            )
            raise LyftIllegalState(error_message)

        if error is None and authorization_code is None:
            error_message = 'Neither query parameter code or error is set.'
            raise LyftIllegalState(error_message)

        if error:
            raise LyftIllegalState(error)

        return authorization_code

    def get_session(self, redirect_url):
        """Complete the Authorization Code Grant process.
        The redirect URL received after the user has authorized
        your application contains an authorization code. Use this
        authorization code to request an access token.
        Parameters
            redirect_url (str)
                The full URL that the Lyft server redirected to after
                the user authorized your app.
        Returns
            (Session)
                A Session object with OAuth 2.0 credentials.
        """
        query_params = self._extract_query(redirect_url)
        authorization_code = self._verify_query(query_params)

        response = request_access_token(
            grant_type=auth.AUTHORIZATION_CODE_GRANT,
            client_id=self.client_id,
            client_secret=self.client_secret,
            code=authorization_code,
        )

        oauth2credential = OAuth2Credential.make_from_response(
            response=response,
            grant_type=auth.AUTHORIZATION_CODE_GRANT,
            client_id=self.client_id,
            client_secret=self.client_secret,
        )

        return Session(oauth2credential=oauth2credential)


class ClientCredentialGrant(OAuth2):
    """Class for Client Credential Grant type.
    This is the (2-legged) flow based authentication for public endpoints.
    The tokens granted here are valid for endpoints that don't require access
    to user data (eg ETA, cost, ride types).
    """

    def __init__(self, client_id, client_secret, scopes, is_sandbox_mode=True):
        """Initialize ClientCredential Class.
        Parameters
            client_id (str)
                Your app's Client ID.
            client_secret (str)
                Your app's Client Secret. This must be kept confidential.
            scopes (set)
                Set of permission scopes to request.
                (e.g. {'public', 'rides.read'})
            is_sandbox_mode (bool)
                Optional. Set to False if your code is in production.
        """
        super(ClientCredentialGrant, self).__init__(client_id, scopes)
        self.client_secret = "-".join([auth.SANDBOX_MODE_PREFIX, client_secret]) if is_sandbox_mode else client_secret

    def get_session(self):
        """Create Session to store credentials.
        Returns
            (Session)
                A Session object with OAuth 2.0 credentials.
        """
        response = request_access_token(
            grant_type=auth.CLIENT_CREDENTIAL_GRANT,
            client_id=self.client_id,
            client_secret=self.client_secret,
            scopes=self.scopes,
        )

        oauth2credential = OAuth2Credential.make_from_response(
            response=response,
            grant_type=auth.CLIENT_CREDENTIAL_GRANT,
            client_id=self.client_id,
            client_secret=self.client_secret,
        )

        return Session(oauth2credential=oauth2credential)


def request_access_token(
    grant_type,
    client_id=None,
    client_secret=None,
    scopes=None,
    code=None,
    refresh_token=None
):
    """Make an HTTP POST to request an access token.
    Parameters
        grant_type (str)
            Either 'client_credientials' (Client Credentials Grant)
            or 'authorization_code' (Authorization Code Grant).
        client_id (str)
            Your app's Client ID.
        client_secret (str)
            Your app's Client Secret.
        scopes (set)
            Set of permission scopes to request.
            (e.g. {'profile', 'history'})
        code (str)
            The authorization code to switch for an access token.
            Only used in Authorization Code Grant.
        refresh_token (str)
            Refresh token used to get a new access token.
            Only used for Authorization Code Grant.
    Returns
        (requests.Response)
            Successful HTTP response from a 'POST' to request
            an access token.
    Raises
        ClientError (APIError)
            Thrown if there was an HTTP error.
    """
    url = build_url(auth.SERVER_HOST, auth.ACCESS_TOKEN_PATH)

    if isinstance(scopes, set):
        scopes = ' '.join(scopes)

    args = {
        'grant_type': grant_type,
        'client_id': client_id,
        'client_secret': client_secret,
        'scope': scopes,
        'code': code,
        'refresh_token': refresh_token,
    }

    auth_header = HTTPBasicAuth(client_id, client_secret)

    response = post(url=url, auth=auth_header, data=args)

    if response.status_code == codes.ok:
        return response

    message = 'Failed to request access token: {}.'
    message = message.format(response.reason)
    raise ClientError(response, message)


def refresh_access_token(credential):
    """Use a refresh token to request a new access token.
    Not suported for access tokens obtained via Implicit Grant.
    Parameters
        credential (OAuth2Credential)
            An authorized user's OAuth 2.0 credentials.
    Returns
        (Session)
            A new Session object with refreshed OAuth 2.0 credentials.
    Raises
        LyftIllegalState (APIError)
            Raised if OAuth 2.0 grant type does not support
            refresh tokens.
    """
    if credential.grant_type == auth.AUTHORIZATION_CODE_GRANT:
        response = request_access_token(
            grant_type=auth.REFRESH_TOKEN,
            client_id=credential.client_id,
            client_secret=credential.client_secret,
            refresh_token=credential.refresh_token,
        )

        oauth2credential = OAuth2Credential.make_from_response(
            response=response,
            grant_type=credential.grant_type,
            client_id=credential.client_id,
            client_secret=credential.client_secret,
        )

        return Session(oauth2credential=oauth2credential)

    elif credential.grant_type == auth.CLIENT_CREDENTIAL_GRANT:
        response = request_access_token(
            grant_type=auth.CLIENT_CREDENTIAL_GRANT,
            client_id=credential.client_id,
            client_secret=credential.client_secret,
            scopes=credential.scopes,
        )

        oauth2credential = OAuth2Credential.make_from_response(
            response=response,
            grant_type=credential.grant_type,
            client_id=credential.client_id,
            client_secret=credential.client_secret,
        )

        return Session(oauth2credential=oauth2credential)

    message = '{} Grant Type does not support Refresh Tokens.'
    message = message.format(credential.grant_type)
    raise LyftIllegalState(message)


def revoke_access_token(credential):
    """Revoke an access token.
    All future requests with the access token will be invalid.
    Parameters
        credential (OAuth2Credential)
            An authorized user's OAuth 2.0 credentials.
    Raises
        ClientError (APIError)
            Thrown if there was an HTTP error.
    """
    url = build_url(auth.SERVER_HOST, auth.REVOKE_PATH)

    args = {
        'token': credential.access_token,
    }

    response = post(url=url, params=args)

    if response.status_code == codes.ok:
        return

    message = 'Failed to revoke access token: {}.'
    message = message.format(response.reason)
    raise ClientError(response, message)
