
class SerializerError(Exception):
    def __init__(self, message):
        self._message = message


class ValidationError(SerializerError):
    pass


class InvalidSerializer(SerializerError):
    pass
