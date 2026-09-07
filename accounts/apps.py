from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """Django app config for the accounts package.

    Registers auth, profile, and password-reset APIs.
    Uses BigAutoField as the default primary key type.
    """

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'
