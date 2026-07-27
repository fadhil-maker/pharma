from django.db import models
from django.contrib.auth.models import User

class ReactionDefinition(models.Model):
    name = models.CharField(max_length=500, unique=True)
    description = models.TextField(blank=True, default='')

    def __str__(self):
        return self.name

class Interaction(models.Model):
    drug_a = models.CharField(max_length=255)
    drug_b = models.CharField(max_length=255)
    reaction = models.ForeignKey(ReactionDefinition, on_delete=models.CASCADE, related_name='interactions')
    severity_slider = models.IntegerField(default=5)  # 1 to 10
    remedy = models.TextField(blank=True, default='')
    time_window_hours = models.IntegerField(default=24)
    organ_bitmask = models.IntegerField(default=0)    # Bitmask for 11 organ systems
    custom_factors = models.JSONField(blank=True, default=dict) # min_age, max_age, min_weight, max_weight, gender

    class Meta:
        unique_together = ('drug_a', 'drug_b')

    def __str__(self):
        return f"{self.drug_a} + {self.drug_b} ({self.severity_slider}/10)"