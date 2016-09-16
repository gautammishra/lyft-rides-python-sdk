# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""Initializes an LyftRidesClient with OAuth 2.0 Credentials.
This example demonstrates how to get an access token through the
OAuth 2.0 Authorization Code Grant and use credentials to create
an LyftRidesClient.
To run this example:
    (1) Set your app credentials in config.yaml
    (2) Run `python authorization_code_grant.py`
    (3) A success message will print, 'Hello {USER_ID}'
    (4) User OAuth 2.0 credentials are recorded in
        'oauth2_session_store.yaml'
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from builtins import input
from yaml import safe_dump

from examples import utils
from examples.utils import fail_print
from examples.utils import response_print
from examples.utils import success_print
from examples.utils import import_app_credentials
from lyft_rides.auth import AuthorizationCodeGrant
from lyft_rides.client import LyftRidesClient
from lyft_rides.errors import ClientError
from lyft_rides.errors import ServerError
from lyft_rides.errors import LyftIllegalState


def authorization_code_grant_flow(credentials, storage_filename):
    """Get an access token through Authorization Code Grant.
    Parameters
        credentials (dict)
            All your app credentials and information
            imported from the configuration file.
        storage_filename (str)
            Filename to store OAuth 2.0 Credentials.
    Returns
        (LyftRidesClient)
            An LyftRidesClient with OAuth 2.0 Credentials.
    """
    auth_flow = AuthorizationCodeGrant(
        credentials.get('client_id'),
        credentials.get('client_secret'),
        credentials.get('scopes'),
    )

    auth_url = auth_flow.get_authorization_url()
    login_message = 'Login and grant access by going to:\n{}\n'
    login_message = login_message.format(auth_url)
    response_print(login_message)

    redirect_url = 'Copy the URL you are redirected to and paste here: \n'
    result = input(redirect_url).strip()

    try:
        session = auth_flow.get_session(result)

    except (ClientError, LyftIllegalState) as error:
        fail_print(error)
        return

    credential = session.oauth2credential

    credential_data = {
        'client_id': credential.client_id,
        'access_token': credential.access_token,
        'expires_in_seconds': credential.expires_in_seconds,
        'scopes': list(credential.scopes),
        'grant_type': credential.grant_type,
        'client_secret': credential.client_secret,
        'refresh_token': credential.refresh_token,
    }

    with open(storage_filename, 'w') as yaml_file:
        yaml_file.write(safe_dump(credential_data, default_flow_style=False))

    return LyftRidesClient(session)


def hello_user(api_client):
    """Use an authorized client to fetch and print profile information.
    Parameters
        api_client (LyftRidesClient)
            An LyftRidesClient with OAuth 2.0 credentials.
    """

    try:
        response = api_client.get_user_profile()

    except (ClientError, ServerError) as error:
        fail_print(error)
        return

    else:
        profile = response.json
        user_id = profile.get('id')
        message = 'Hello. Successfully granted access token to User ID {}.'.format(user_id)
        success_print(message)


if __name__ == '__main__':
    """Run the example.
    Get an access token through the OAuth 2.0 Authorization Code Grant
    and use credentials to create an LyftRidesClient.
    """
    credentials = import_app_credentials()

    api_client = authorization_code_grant_flow(
        credentials,
        utils.STORAGE_FILENAME,
    )

    credentials.get

    hello_user(api_client)