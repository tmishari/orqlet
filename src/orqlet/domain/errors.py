"""Errors raised by the pure domain. Every one carries a message safe to show to a user."""


class OrqletError(Exception):
    """Base class for errors that Orqlet raises on purpose."""


class InvalidPath(OrqletError):
    """A path cannot be reduced to a canonical, safe, repository-relative form."""


class CanonicalJsonError(OrqletError):
    """A value is outside the canonical JSON subset that Orqlet hashes."""


class InvalidVersion(OrqletError):
    """A version string is not a three-part release number."""
