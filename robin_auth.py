
from robin_stocks.authentication import generate_device_token, respond_to_challenge
import robin_stocks.urls as urls
import robin_stocks.helper as helper
import getpass
import random
import pickle
import os

def _post_to_login(username, password, challenge_type='sms'):
    payload = {
      'client_id': 'c82SH0WZOsabOXGP2sxqcj34FxkvfnWRZBKlBjFS',
      'expires_in': 86400,
      'grant_type': 'password',
      'password': password,
      'scope': 'internal',
      'username': username,
      'challenge_type': challenge_type,
      'device_token':'3559a85e-0726-eec9-e83b-6c6803d6ddad'} # TODO: make device-specific.
    return helper.request_post(urls.login_url(), payload)

def _save_credentials(data):
    token = '{0} {1}'.format(data['token_type'], data['access_token'])
    set_token(token)
    return token

def login(username, password, challenge_type = "sms"):
  data = _post_to_login(username, password)
  # Challenge type is used if not logging in with two-factor authentication.
  if 'challenge' in data:
    return None, data['challenge']['id']
  elif 'access_token' in data:
    return _save_credentials(data), None
  elif data.get('detail', None) == 'Unable to log in with provided credentials.':
    raise InvalidCredentialsError()
  else:
    print(data)
    raise AuthError(data)

def send_challenge_response(username, password, challenge_id, sms_code):
  respond_to_challenge(challenge_id, sms_code)
  helper.update_session('X-ROBINHOOD-CHALLENGE-RESPONSE-ID', challenge_id)
  data = _post_to_login(username, password)
  if 'access_token' in data:
    return _save_credentials(data)
  else:
    print(data)
    raise AuthError(data)

def set_token(token):
  helper.update_session('Authorization', token)
  helper.set_login_state(True)


class AuthError(Exception):
  pass

class InvalidCredentialsError(AuthError):
  pass