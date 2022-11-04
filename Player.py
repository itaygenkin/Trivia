class Player:
    """
    This class is intended to replace user object
    """
    def __init__(self, username, password, points=0):
        self._username = username
        self._password = password
        self._points = points
        self._is_creator = False

    def get_username(self):
        return self._username

    def check_password(self, pwd):
        return pwd == self._password

    def get_points(self):
        return self._points

    def make_up_a_creator(self, player):
        if self._is_creator:
            player._is_creator = True
        else:
            raise PermissionError
