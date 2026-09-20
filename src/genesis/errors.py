class GenesisError(Exception):
    """Base for errors Genesis raises deliberately."""


class InputUnavailableError(GenesisError):
    """Interactive input was needed but stdin was exhausted."""


class AdapterError(GenesisError):
    """Adapter backend failed"""


class AdapterAuthError(AdapterError):
    """Credential for adapter backend rejected."""
