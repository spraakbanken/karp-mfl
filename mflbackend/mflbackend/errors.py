

class MflException(Exception):
    def __init__(self, message, status_code=400, code="error"):
        super(MflException, self).__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
