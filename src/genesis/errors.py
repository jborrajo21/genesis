class GenesisError(Exception):
    """Base for errors Genesis raises deliberately."""


class InputUnavailableError(GenesisError):
    """Interactive input was needed but stdin was exhausted."""
