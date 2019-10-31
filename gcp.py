"""Contains functions related to the Google Cloud Platform."""

import datetime
import json

import jwt
import requests


def get_token():
    """Fetches service account access token."""
    secrets = get_secrets()
    jwt = generate_jwt(secrets)

    # POST data
    payload = {'assertion': jwt}
    payload['grant_type'] = 'urn:ietf:params:oauth:grant-type:jwt-bearer'

    url = secrets['token_uri']
    response = requests.post(url, data=payload)

    return response.json()


def generate_jwt(secrets):
    """Generates and signs the jwt needed to retrieve the access token.

    Args:
        secrets: A dictionary containing the secret values needed to create
            and sign the jwts

    Returns:
        A str representing the Base64 encoded jwt
    """
    payload = {'iss': secrets['client_email']}
    payload['scope'] = 'https://www.googleapis.com/auth/devstorage.read_write'

    payload['aud'] = secrets['token_uri']
    payload['iat'] = get_utc_timestamp()
    payload['exp'] = get_utc_timestamp() + datetime.timedelta(seconds=60)

    jwt_token = jwt.encode(payload, secrets['private_key'], algorithm='RS256')
    return jwt_token.decode('utf-8')


def get_utc_timestamp():
    return datetime.datetime.now(datetime.timezone.utc)


def get_secrets():
    """Retrieves secrets stored on config file

    Returns:
        A dictionary containing the various secrets
    """
    with open('secrets.json') as file:
        return json.load(file)
