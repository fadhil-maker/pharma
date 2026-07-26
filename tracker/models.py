from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class ReactionDefinition(models.Model):
    """
    A master clinical reaction description.
    Examples: 'Serotonin Syndrome', 'Hepatotoxicity', 'QT Prolongation'.
    Names are auto-normalized to lowercase for case-insensitive matching.
    """
    name = models.CharField(max_length=300, unique=True)

    def save(self, *args, **kwargs):
        """Normalize reaction name to lowercase before persistence."""
        if self.name:
            self.name = self.name.strip().lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name = 'Reaction Definition'
        verbose_name_plural = 'Reaction Definitions'


class Interaction(models.Model):
    """
    Maps a drug-drug interaction by generic Active Chemical Ingredient names
    (INN / brand-agnostic). Uses CharField instead of ForeignKey so the system
    tracks by standardized generic names (e.g., 'paracetamol', 'aspirin')
    independent of any local commercial brand packaging.

    custom_factors (JSONField) stores fluid clinical constraints without
    schema changes:
        {
            "min_age": 18,
            "max_age": 65,
            "min_weight": 40,
            "max_weight": 120,
            "gender": "female"
        }
    """
    drug_a = models.CharField(
        max_length=300,
        help_text='Generic / INN name of first active ingredient (auto-lowercased)'
    )
    drug_b = models.CharField(
        max_length=300,
        help_text='Generic / INN name of second active ingredient (auto-lowercased)'
    )
    reaction = models.ForeignKey(
        ReactionDefinition,
        on_delete=models.CASCADE,
        related_name='interactions'
    )
    severity_slider = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text='Severity index from 1 (minor) to 10 (critical contraindication)'
    )
    remedy = models.TextField(
        blank=True,
        default='',
        help_text='Clinical remedy instructions returned with warnings'
    )
    time_window_hours = models.IntegerField(
        default=24,
        help_text='Clearance / time-to-react window in hours'
    )
    custom_factors = models.JSONField(
        default=dict,
        blank=True,
        help_text='Dynamic pathology constraints: min_age, max_age, min_weight, max_weight, gender'
    )

    def save(self, *args, **kwargs):
        """Normalize generic drug names to lowercase before persistence."""
        if self.drug_a:
            self.drug_a = self.drug_a.strip().lower()
        if self.drug_b:
            self.drug_b = self.drug_b.strip().lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.drug_a} + {self.drug_b} => {self.reaction.name}"

    class Meta:
        unique_together = ('drug_a', 'drug_b', 'reaction')
        ordering = ['-severity_slider', 'drug_a']
        verbose_name = 'Drug Interaction'
        verbose_name_plural = 'Drug Interactions'


class DrugClassMapping(models.Model):
    """
    Maps individual drug names / brand names to active class tags (e.g. 'ibuprofen' -> '@nsaid').
    """
    drug_name = models.CharField(max_length=300, unique=True)
    class_tag = models.CharField(max_length=100)

    def save(self, *args, **kwargs):
        if self.drug_name:
            self.drug_name = self.drug_name.strip().lower()
        if self.class_tag:
            self.class_tag = self.class_tag.strip().lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.drug_name} -> {self.class_tag}"