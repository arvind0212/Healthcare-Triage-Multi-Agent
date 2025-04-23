from .settings import Settings

_settings_instance = None

def get_config() -> Settings:
    """Returns the singleton instance of the Settings."""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance

# Optionally, you might want a way to reset for testing
def reset_config():
    """Resets the singleton instance (useful for testing)."""
    global _settings_instance
    _settings_instance = None
