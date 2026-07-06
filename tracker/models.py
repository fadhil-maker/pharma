from django.db import models

# Create your models here.
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

class ReactionDefinition(models.Model):
    name = models.CharField(max_length=200, unique=True)
    category = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.name

class Drug(models.Model):
    name = models.CharField(max_length=200, unique=True)
    active_components = models.TextField()
    activation_time_mins = models.IntegerField(help_text="Minutes until drug takes effect")
    clearance_time_hours = models.FloatField(help_text="Hours until drug leaves bloodstream")

    def __str__(self):
        return self.name

class Interaction(models.Model):
    drug_a = models.ForeignKey(Drug, on_delete=models.CASCADE, related_name="interactions_as_a")
    drug_b = models.ForeignKey(Drug, on_delete=models.CASCADE, related_name="interactions_as_b")
    reaction = models.ForeignKey(ReactionDefinition, on_delete=models.CASCADE)
    severity_slider = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(10)])

    class Meta:
        unique_together = ('drug_a', 'drug_b', 'reaction')

    def __str__(self):
        return f"{self.drug_a.name} + {self.drug_b.name} = {self.reaction.name}"