********************************
Unofficial Lyft Rides Python SDK
********************************

Python SDK (beta) to support the `Lyft Rides API <https://developer.lyft.com/docs/>`_.

Installation
------------

To use the Unofficial Lyft Rides Python SDK:

.. code-block:: bash

    $ pip install lyft_rides


Head over to `pip-installer <http://www.pip-installer.org/en/latest/index.html>`_ for instructions on installing pip.

To run from source, you can `download the source code <https://github.com/gautammishra/lyft-rides-python-sdk/archive/master.zip>`_ for lyft-rides, and then run:

.. code-block:: bash

    $ python setup.py install


We recommend using `virtualenv <http://www.virtualenv.org/>`_ when setting up your project environment. You may need to run the above commands with `sudo` if you’re not using it.

Read-Only Use
-------------

If you just need access to resources that are not user-specific (eg. ETA, cost, ride types) you will go through a "2-legged" flow. In this case, you can create a Session using ClientCredentialGrant with the Client ID and Client Secret you received after `registering your app <https://www.lyft.com/developers/manage>`_.

.. code-block:: python

    from lyft_rides.auth import ClientCredentialGrant
    from lyft_rides.session import Session

    auth_flow = ClientCredentialGrant(
	YOUR_CLIENT_ID,
	YOUR_CLIENT_SECRET,
	YOUR_PERMISSION_SCOPES,
	)
    session = auth_flow.get_session()

Use this Session to create an LyftRidesClient and fetch API resources:

.. code-block:: python

    from lyft_rides.client import LyftRidesClient

    client = LyftRidesClient(session)
    response = client.get_ride_types(37.7833, -122.4167)
    ride_types = response.json.get('ride_types')

Authorization
-------------

If you need access to a Lyft user's account in order to make requests on their behalf, you will go through a "3-legged" flow. In this case, you will need the user to grant access to your application through the OAuth 2.0 Authorization Code flow. See `Lyft API docs <https://developer.lyft.com/docs/authentication>`_.

The Authorization Code flow is a two-step authorization process. The first step is having the user authorize your app and the second involves requesting an OAuth 2.0 access token from Lyft. This process is mandatory if you want to take actions on behalf of a user or access their information.

.. code-block:: python

    from lyft_rides.auth import AuthorizationCodeGrant
    auth_flow = AuthorizationCodeGrant(
        YOUR_CLIENT_ID,
        YOUR_CLIENT_SECRET,
	YOUR_PERMISSION_SCOPES,
    )
    auth_url = auth_flow.get_authorization_url()

Navigate the user to the `auth_url` where they can grant access to your application. After, they will be redirected to a `redirect_url` with the format REDIRECT_URL?code=UNIQUE_AUTH_CODE. Use this `redirect_url` to create a session and start LyftRidesClient.

.. code-block:: python

    session = auth_flow.get_session(redirect_url)
    client = LyftRidesClient(session)
    credentials = session.oauth2credential

Keep `credentials` information in a secure data store and reuse them to make API calls on behalf of your user. The SDK will handle the token refresh for you automatically when it makes API requests with a LyftRidesClient.


Example Usage
-------------

Navigate to the `examples` folder to access the python scripts examples.  Before you can run an example, you must edit the `example/config.yaml` file and add your app credentials.

To get an LyftRidesClient through the Authorization Code flow, run:

.. code-block:: bash

    $ python examples/authorization_code_grant.py

The example above stores user credentials in `examples/oauth2_session_store.yaml`.

Get Available Products
""""""""""""""""""""""

.. code-block:: python

    response = client.get_ride_types(37.7833, -122.4167)
    ride_types = response.json.get('ride_types')
    ride_type = ride_types[0].get('ride_type')

Request a Ride
""""""""""""""

.. code-block:: python

    response = client.request_ride(
        ride_type=ride_type,
        start_latitude=37.77,
        start_longitude=-122.41,
        end_latitude=37.79,
        end_longitude=-122.41,
    )
    ride_details = response.json
    ride_id = ride_details.get('ride_id')


This does not make a real-time request. It makes a request to the sandbox environment.

To send a real-time request to send a Lyft driver to the specified start location, make sure to instantiate your ClientCredentialGrant with

.. code-block:: python

    auth_flow = ClientCredentialGrant(
	YOUR_CLIENT_ID,
	YOUR_CLIENT_SECRET,
	YOUR_PERMISSION_SCOPES,
	sandbox_mode=False)

or AuthorizationCodeGrant with

.. code-block:: python

    auth_flow = AuthorizationCodeGrant(
        YOUR_CLIENT_ID,
        YOUR_CLIENT_SECRET,
	YOUR_PERMISSION_SCOPES,
	sandbox_mode=False,
    )

The default for `sandbox_mode` is set to `True`. See the `documentation <https://developer.lyft.com/docs/sandbox>`_ to read more about using the Sandbox Environment.

Getting help
------------

For full documentation about Lyft Rides API, visit the `Lyft Developer Site <https://developer.lyft.com/>`_.

Contributing
------------

If you've found a bug in the library or would like new features added, go ahead and open issues or pull requests against this repository.
