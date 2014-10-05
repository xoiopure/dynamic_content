from http import cookies

from . import session, users


__author__ = 'justusadam'

SESSION_TOKEN_IDENTIFIER = 'SESS'

# special usernames
UNKNOWN = -2
ANONYMOUS = -1

# special access groups
UNKNOWN_GRP = -2
ANONYMOUS_GRP = -1
AUTH = 1


class ClientInformation:
  def __init__(self, headers):
    self._headers = headers
    if 'Cookie' in headers:
      self._cookies = cookies.SimpleCookie(headers['Cookie'])
    else:
      self._cookies = None
    # user and group are initially set to UNKNOWN and only resolved when necessary
    self._user = UNKNOWN
    self._access_group = UNKNOWN_GRP

  @property
  def headers(self):
    return self._headers

  @property
  def user(self):
    if self._user == UNKNOWN:
      self._user = self.auth_user()
    return self._user

  @property
  def access_group(self):
    if self._access_group == UNKNOWN_GRP:
      self._access_group = self.get_acc_grp(self.user)
    return self._access_group

  def auth_user(self):
    return -1

  def get_acc_grp(self, user):
    return 0

  @user.setter
  def user(self, value):
    self._user = value

  @property
  def cookies(self):
    return self._cookies

  def check_permission(self, permission):
    return users.check_permission(self.access_group, permission)


class ClientInfoImpl(ClientInformation):
  def __init__(self, headers):
    super().__init__(headers)

  def get_acc_grp(self, user):
    if user == ANONYMOUS:
      return ANONYMOUS
    else:
      return users.acc_grp(user)

  def auth_user(self):
    if self._cookies:
      if SESSION_TOKEN_IDENTIFIER in self._cookies:
        db_result = session.validate_session(self._cookies[SESSION_TOKEN_IDENTIFIER].value)
        if db_result is not None:
          return db_result
    return -1