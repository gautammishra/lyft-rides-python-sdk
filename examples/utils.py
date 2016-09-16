# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""General utilities for command line examples."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from collections import namedtuple
from yaml import safe_load

from lyft_rides.client import LyftRidesClient
from lyft_rides.session import OAuth2Credential
from lyft_rides.session import Session


# set your app credentials here
CREDENTIALS_FILENAME = 'config.yaml'

# where your OAuth 2.0 credentials are stored
STORAGE_FILENAME = 'oauth2_session_store.yaml'

DEFAULT_CONFIG_VALUES = frozenset([
    'INSERT_CLIENT_ID_HERE',
    'INSERT_CLIENT_SECRET_HERE',
])

Colors = namedtuple('Colors', 'response, success, fail, end')
COLORS = Colors(
    response='\033[94m',
    success='\033[92m',
    fail='\033[91m',
    end='\033[0m',
)


def success_print(message):
    """Print a message in green text.
    Parameters
        message (str)
            Message to print.
    """
    print(COLORS.success, message, COLORS.end)


def response_print(message):
    """Print a message in blue text.
    Parameters
        message (str)
            Message to print.
    """
    print(COLORS.response, message, COLORS.end)


def fail_print(error):
    """Print an error in red text.
    Parameters
        error (HTTPError)
            Error object to print.
    """
    print(COLORS.fail, error.message, COLORS.end)
    print(COLORS.fail, error.errors, COLORS.end)


def paragraph_print(message):
    """Print message with padded newlines.
    Parameters
        message (str)
            Message to print.
    """
    paragraph = '\n{}\n'
    print(paragraph.format(message))


def import_app_credentials(filename=CREDENTIALS_FILENAME):
    """Import app credentials from configuration file.
    Parameters
        filename (str)
            Name of configuration file.
    Returns
        credentials (dict)
            All your app credentials and information
            imported from the configuration file.
    """
    with open(filename, 'r') as config_file:
        config = safe_load(config_file)

    client_id = config['client_id']
    client_secret = config['client_secret']

    config_values = [client_id, client_secret]

    for value in config_values:
        if value in DEFAULT_CONFIG_VALUES:
            exit('Missing credentials in {}'.format(filename))

    credentials = {
        'client_id': client_id,
        'client_secret': client_secret,
        'scopes': set(config['scopes']),
    }

    return credentials


def import_oauth2_credentials(filename=STORAGE_FILENAME):
    """Import OAuth 2.0 session credentials from storage file.
    Parameters
        filename (str)
            Name of storage file.
    Returns
        credentials (dict)
            All your app credentials and information
            imported from the configuration file.
    """
    with open(filename, 'r') as storage_file:
        storage = safe_load(storage_file)

    # depending on OAuth 2.0 grant_type, these values may not exist
    client_secret = storage.get('client_secret')
    refresh_token = storage.get('refresh_token')

    credentials = {
        'access_token': storage['access_token'],
        'client_id': storage['client_id'],
        'client_secret': client_secret,
        'expires_in_seconds': storage['expires_in_seconds'],
        'grant_type': storage['grant_type'],
        'refresh_token': refresh_token,
        'scopes': storage['scopes'],
    }

    return credentials


def create_lyft_client(credentials):
    """Create an LyftRidesClient from OAuth 2.0 credentials.
    Parameters
        credentials (dict)
            Dictionary of OAuth 2.0 credentials.
    Returns
        (LyftRidesClient)
            An authorized LyftRidesClient to access API resources.
    """
    oauth2credential = OAuth2Credential(
        client_id=credentials.get('client_id'),
        access_token=credentials.get('access_token'),
        expires_in_seconds=credentials.get('expires_in_seconds'),
        scopes=credentials.get('scopes'),
        grant_type=credentials.get('grant_type'),
        client_secret=credentials.get('client_secret'),
        refresh_token=credentials.get('refresh_token'),
    )
    session = Session(oauth2credential=oauth2credential)
    return LyftRidesClient(session)