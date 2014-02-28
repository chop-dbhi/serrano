from django.contrib import admin
from .models import ApiToken


class ApiTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'token', 'revoked', 'created')
    list_editable = ('revoked',)
    list_filter = ('user', 'revoked')
    fields = ('user', 'token_display', 'revoked')
    readonly_fields = ('token_display',)

    def token_display(self, instance):
        if instance.pk:
            return instance.token
        return '<em>(displayed once saved)</em>'

    token_display.short_description = 'Token'
    token_display.allow_tags = True

admin.site.register(ApiToken, ApiTokenAdmin)
