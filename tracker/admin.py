from django.contrib import admin
from .models import ReactionDefinition, Interaction


@admin.register(ReactionDefinition)
class ReactionDefinitionAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)
    list_per_page = 50


@admin.register(Interaction)
class InteractionAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'drug_a', 'drug_b', 'reaction',
        'severity_slider', 'short_remedy',
    )
    search_fields = ('drug_a', 'drug_b')
    list_filter = ('severity_slider', 'reaction')
    list_per_page = 50

    @admin.display(description='Remedy (preview)')
    def short_remedy(self, obj):
        """Show truncated remedy text in admin list view."""
        if obj.remedy and len(obj.remedy) > 80:
            return obj.remedy[:80] + '…'
        return obj.remedy or '—'