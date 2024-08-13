class EnvironmentVarsException(Exception):
    """Класс исключений при отсутствии переменных окружения."""

    pass


class NotHttp200StatusException(Exception):
    """Класс исключений при статусе ответа != 200."""

    pass
