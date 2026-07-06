from django.contrib import admin
from .models import Drug, ReactionDefinition, Interaction

@admin.register(Drug)
class DrugAdmin(admin.ModelAdmin):
    list_display = ('name', 'activation_time_mins', 'clearance_time_hours')
    search_fields = ('name', 'active_components')

@admin.register(ReactionDefinition)
class ReactionDefinitionAdmin(admin.ModelAdmin):
    list_display = ('name', 'category')
    search_fields = ('name',)

@admin.register(Interaction)
class InteractionAdmin(admin.ModelAdmin):
    list_display = ('drug_a', 'drug_b', 'reaction', 'severity_slider')
    autocomplete_fields = ['drug_a', 'drug_b', 'reaction']