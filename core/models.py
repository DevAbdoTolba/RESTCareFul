from django.db import models


class SiteSettings(models.Model):
    """Singleton row for site-wide settings (currently just the active theme).

    The admin's theme choice is stored here, not in a browser, so it applies to
    EVERY user on every new session — whoever the admin picks the theme for.
    """

    theme = models.CharField(max_length=50, default='default')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'site settings'

    def __str__(self) -> str:
        return f'SiteSettings(theme={self.theme})'

    @classmethod
    def load(cls):
        """Get (or lazily create) the single settings row."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
