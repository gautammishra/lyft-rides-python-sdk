# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

try:
    from future.utils import viewitems
except ImportError:
    viewitems = None


class APIError(Exception):
    """Parent class of all Lyft API errors."""
    pass


class HTTPError(APIError):
    """Parent class of all HTTP errors."""

    def _adapt_response(self, response):
        """Convert error responses to standardized ErrorDetails."""
        if 'application/json' in response.headers['content-type']:
            body = response.json()
            status = response.status_code

            if body.get('error'):
                return self._simple_response_to_error_adapter(status, body)

        raise UnknownHttpError(response)

    def _simple_response_to_error_adapter(self, status, original_body):
        """Convert a single error response."""
        meta = original_body.get('error')
        e = []

        if 'error_detail' in original_body:
            errors = original_body.get('error_detail')

            for error in errors:
                if type(error) == dict:
                    if viewitems:
                        items = viewitems(error)
                    else:
                        items = error.items()
                    for parameter, title in items:
                        e.append(ErrorDetails(parameter, title))
        elif 'error_description' in original_body:
            e.append(original_body.get('error_description'))

        return e, meta


class ClientError(HTTPError):
    """Raise for 4XX Errors.
    Contains an array of ErrorDetails objects.
    """

    def __init__(self, response, message=None):
        """
        Parameters
            response
                The 4XX HTTP response.
            message
                An error message string. If one is not provided, the
                default message is used.
        """
        if not message:
            message = (
                'The request contains bad syntax or cannot be filled '
                'due to a fault from the client sending the request.'
            )

        super(ClientError, self).__init__(message)
        errors, meta = super(ClientError, self)._adapt_response(response)
        self.errors = errors
        self.meta = meta
        self.response = response


class ServerError(HTTPError):
    """Raise for 5XX Errors.
    Contains a single ErrorDetails object.
    """

    def __init__(self, response, message=None):
        """
        Parameters
            response
                The 5XX HTTP response.
            message
                An error message string. If one is not provided, the
                default message is used.
        """
        if not message:
            message = (
                'The server encounter an error or is '
                'unable to process the request.'
            )

        super(ServerError, self).__init__(message)
        self.error, self.meta = self._adapt_response(response)
        self.response = response

    def _adapt_response(self, response):
        """Convert various error responses to standardized ErrorDetails."""
        errors, meta = super(ServerError, self)._adapt_response(response)
        return errors[0] if errors else None, meta  # single error instead of array


class ErrorDetails(object):
    """Class to standardize all errors."""

    def __init__(self, parameter, title):
        self.parameter = parameter
        self.title = title

    def __repr__(self):
        return '"{}" - {}'.format(
            str(self.parameter),
            str(self.title)
        )


class UnknownHttpError(APIError):
    """Throw when an unknown HTTP error occurs.
    Thrown when a previously unseen error is
    received and there is no standard schema to convert
    it into a well-formed HttpError.
    """

    def __init__(self, response):
        super(UnknownHttpError, self).__init__()
        self.response = response


class LyftIllegalState(APIError):
    """Raise for Illegal State Errors.
    Thrown when the environment or class is not in an
    appropriate state for the requested operation.
    """
pass