import os
from typing import Optional


class ProfileResolver:
    """
    Resolves the active Spring-style profile from the environment.
    Reads ``NESTIFYPY_PROFILE`` (or ``SPRING_PROFILES_ACTIVE`` as fallback).
    """

    @staticmethod
    def resolve() -> Optional[str]:
        return (
            os.environ.get("NESTIFYPY_PROFILE")
            or os.environ.get("SPRING_PROFILES_ACTIVE")
            or None
        )
