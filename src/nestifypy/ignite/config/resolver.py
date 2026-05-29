from typing import Any

from nestifypy.ignite.config.properties import Properties


class ValueResolver:
    """
    Resolves ``@Value``-style injection keys from the Properties store.
    """

    def __init__(self, properties: Properties):
        self._properties = properties

    def resolve(self, key: str, required: bool = True) -> Any:
        value = self._properties.get(key)
        if value is None and required:
            from nestifypy.ignite.core.exceptions import ValueInjectionException
            raise ValueInjectionException(key)
        return value
