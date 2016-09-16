# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""Python client for the Lyft API.
This client is designed to make calls to the Lyft API.
An LyftRidesClient is instantiated with a Session which holds either
your server token or OAuth 2.0 credentials. Your usage of this
module might look like:
    client = LyftRidesClient(session)
    products = client.get_ride_types(latitude, longitude)
    profile = client.get_user_profile()
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from collections import OrderedDict

from lyft_rides.auth import refresh_access_token
from lyft_rides.auth import revoke_access_token
from lyft_rides.request import Request
from lyft_rides.utils import auth


VALID_RIDE_STATUS = frozenset([
    'pending',
    'accepted',
    'arrived',
    'pickedUp',
    'droppedOff',
    'canceled',
])


class LyftRidesClient(object):
    """Class to make calls to the Lyft API."""

    def __init__(self, session):
        """Initialize an LyftRidesClient.
        Parameters
            session (Session)
                The Session object containing access credentials.
        """
        self.session = session
        self.api_host = auth.SERVER_HOST

    def _api_call(self, method, target, args=None):
        """Create a Request object and execute the call to the API Server.
        Parameters
            method (str)
                HTTP request (e.g. 'POST').
            target (str)
                The target URL with leading slash (e.g. '/v1/products').
            args (dict)
                Optional dictionary of arguments to attach to the request.
        Returns
            (Response)
                The server's response to an HTTP request.
        """
        self.refresh_oauth_credential()

        request = Request(
            auth_session=self.session,
            api_host=self.api_host,
            method=method,
            path=target,
            args=args,
        )

        return request.execute()

    def get_ride_types(self, latitude, longitude, ride_type=None):
        """Get information about the Ride Types offered by Lyft at a given location.
        Parameters
            latitude (float)
                The latitude component of a location.
            longitude (float)
                The longitude component of a location.
            ride_type (str)
                Optional specific ride type information only.
        Returns
            (Response)
                A Response object containing available ride_type(s) information.
        """
        args = OrderedDict([
            ('lat', latitude),
            ('lng', longitude),
            ('ride_type', ride_type),
        ])

        return self._api_call('GET', 'v1/ridetypes', args=args)

    def get_pickup_time_estimates(self, latitude, longitude, ride_type=None):
        """Get pickup time estimates (ETA) for products at a given location.
        Parameters
            latitude (float)
                The latitude component of a location.
            longitude (float)
                The longitude component of a location.
            ride_type (str)
                Optional specific ride type pickup estimate only.
        Returns
            (Response)
                A Response containing each product's pickup time estimates.
        """
        args = OrderedDict([
            ('lat', latitude),
            ('lng', longitude),
            ('ride_type', ride_type),
        ])

        return self._api_call('GET', 'v1/eta', args=args)

    def get_cost_estimates(
        self,
        start_latitude,
        start_longitude,
        end_latitude=None,
        end_longitude=None,
        ride_type=None,
    ):
        """Get cost estimates (in cents) for rides at a given location.
        Parameters
            start_latitude (float)
                The latitude component of a start location.
            start_longitude (float)
                The longitude component of a start location.
            end_latitude (float)
                Optional latitude component of a end location.
                If the destination parameters are not supplied, the endpoint will
                simply return the Prime Time pricing at the specified location.
            end_longitude (float)
                Optional longitude component of a end location.
                If the destination parameters are not supplied, the endpoint will
                simply return the Prime Time pricing at the specified location.
             ride_type (str)
                Optional specific ride type price estimate only.
        Returns
            (Response)
                A Response object containing each product's price estimates.
        """
        args = OrderedDict([
            ('start_lat', start_latitude),
            ('start_lng', start_longitude),
            ('end_lat', end_latitude),
            ('end_lng', end_longitude),
            ('ride_type', ride_type),
        ])

        return self._api_call('GET', 'v1/cost', args=args)

    def get_drivers(self, latitude, longitude):
        """Get information about the location of drivers available near a location.
        A list of 5 locations for a sample of drivers for each ride type will be provided.
        Parameters
            latitude (float)
                The latitude component of a location.
            longitude (float)
                The longitude component of a location.
        Returns
            (Response)
                A Response object containing available drivers information
                near the specified location.
        """
        args = OrderedDict([
            ('lat', latitude),
            ('lng', longitude),
        ])

        return self._api_call('GET', 'v1/drivers', args=args)

    def request_ride(
        self,
        ride_type=None,
        start_latitude=None,
        start_longitude=None,
        start_address=None,
        end_latitude=None,
        end_longitude=None,
        end_address=None,
        primetime_confirmation_token=None,
    ):
        """Request a ride on behalf of an Lyft user.
        Parameters
            ride_type (str)
                Name of the type of ride you're requesting.
                E.g., lyft, lyft_plus
            start_latitude (float)
                Latitude component of a start location.
            start_longitude (float)
                Longitude component of a start location.
            start_address (str)
                Optional pickup address.
            end_latitude (float)
                Optional latitude component of a end location.
                Destination would be NULL in this case.
            end_longitude (float)
                Optional longitude component of a end location.
                Destination would be NULL in this case.
            end_address (str)
                Optional destination address.
            primetime_confirmation_token (str)
                Optional string containing the Prime Time confirmation token
                to book rides having Prime Time Pricing.
        Returns
            (Response)
                A Response object containing the ride request ID and other
                details about the requested ride..
        """
        args = {
            'ride_type': ride_type,
            'origin': {
                'lat': start_latitude,
                'lng': start_longitude,
                'address': start_address,
            },
            'destination': {
                'lat': end_latitude,
                'lng': end_longitude,
                'address': end_address,
            },
            'primetime_confirmation_token': primetime_confirmation_token,
        }

        return self._api_call('POST', 'v1/rides', args=args)

    def get_ride_details(self, ride_id):
        """Get status details about an ongoing or past ride.
        Params
            ride_id (str)
                The unique ID of the Ride Request.
        Returns
            (Response)
                A Response object containing the ride's
                status, location, driver, and other details.
        """
        endpoint = 'v1/rides/{}'.format(ride_id)
        return self._api_call('GET', endpoint)

    def cancel_ride(self, ride_id, cancel_confirmation_token=None):
        """Cancel an ongoing ride on behalf of a user.
        Params
            ride_id (str)
                The unique ID of the Ride Request.
            cancel_confirmation_token (str)
                Optional string containing the cancellation confirmation token.
        Returns
            (Response)
                A Response object with successful status_code
                if ride was canceled.
        """
        args = {
            "cancel_confirmation_token": cancel_confirmation_token
        }
        endpoint = 'v1/rides/{}/cancel'.format(ride_id)
        return self._api_call('POST', endpoint, args=args)

    def rate_tip_ride(self,
        ride_id,
        rating,
        tip_amount=None,
        tip_currency=None,
        feedback=None
    ):
        """Provide a rating, tip or feedback for the specified ride.
        Params
            ride_id (str)
                The unique ID of the Ride Request.
            rating (int)
                An integer between 1 and 5
            tip_amount
                Optional integer amount greater than 0 in minor currency units e.g. 200 for $2
            tip_currency
                Optional 3-character currency code e.g. 'USD'
            feedback
                Optional feedback message
        Returns
            (Response)
                A Response object with successful status_code
                if rating was submitted.
        """
        args = {
            "rating": rating,
            "tip.amount": tip_amount,
            "tip.currency": tip_currency,
            "feedback": feedback,
        }

        endpoint = 'v1/rides/{}/rating'.format(ride_id)
        return self._api_call('PUT', endpoint, args=args)

    def get_ride_receipt(self, ride_id):
        """Get receipt information from a completed ride.
        Params
            ride_id (str)
                The unique ID of the Ride Request.
        Returns
            (Response)
                A Response object containing the charges for
                the given ride.
        """
        endpoint = 'v1/rides/{}/receipt'.format(ride_id)
        return self._api_call('GET', endpoint)

    def get_user_ride_history(self, start_time, end_time, limit=None):
        """Get activity about the user's lifetime activity with Lyft.
        Parameters
            start_time (datetime)
                Restrict to rides starting after this point in time.
                The earliest supported date is 2015-01-01T00:00:00Z
            end_time (datetime)
                Optional Restrict to rides starting before this point in time.
                The earliest supported date is 2015-01-01T00:00:00Z
            limit (int)
                Optional integer amount of results to return. Default is 10.
        Returns
            (Response)
                A Response object containing ride history.
        """
        args = {
            'start_time': start_time,
            'end_time': end_time,
            'limit': limit,
        }

        return self._api_call('GET', 'v1/rides', args=args)

    def get_user_profile(self):
        """Get information about the authorized Lyft user.
        Returns
            (Response)
                A Response object containing account information.
        """
        return self._api_call('GET', 'v1/profile')

    def refresh_oauth_credential(self):
        """Refresh session's OAuth 2.0 credentials if they are stale."""
        credential = self.session.oauth2credential

        if credential.is_stale():
            refresh_session = refresh_access_token(credential)
            self.session = refresh_session

    def revoke_oauth_credential(self):
        """Revoke the session's OAuth 2.0 credentials."""
        credential = self.session.oauth2credential
        revoke_access_token(credential)
