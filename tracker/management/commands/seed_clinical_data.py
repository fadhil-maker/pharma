import json
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from tracker.models import ReactionDefinition, Interaction, DrugClassMapping

class Command(BaseCommand):
    help = "Seed clinical database with reactions, interactions, and drug class mappings."

    def handle(self, *args, **kwargs):
        self.stdout.write("Seeding clinical database...")
        
        # Load JSON files
        tracker_dir = os.path.join(settings.BASE_DIR, 'tracker')
        
        drug_classes = {}
        interaction_rules = []
        
        try:
            with open(os.path.join(tracker_dir, 'drug_classes.json'), 'r') as f:
                drug_classes = json.load(f)
            with open(os.path.join(tracker_dir, 'interaction_rules.json'), 'r') as f:
                interaction_rules = json.load(f)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error loading JSON files: {e}"))
            return

        # 1. Seed DrugClassMapping
        mapped_count = 0
        for drug_name, class_tag in drug_classes.items():
            _, created = DrugClassMapping.objects.get_or_create(
                drug_name=drug_name.strip().lower(),
                defaults={'class_tag': class_tag.strip().lower()}
            )
            if created:
                mapped_count += 1
        self.stdout.write(self.style.SUCCESS(f"Seeded {mapped_count} new drug-to-class mappings."))

        # 2. Seed Reactions & Interactions
        rules_count = 0
        for rule in interaction_rules:
            rx_name = rule.get('reaction', 'General Conflict').strip().lower()
            rx_obj, _ = ReactionDefinition.objects.get_or_create(name=rx_name)

            drug_a = rule.get('group_a', '').strip().lower()
            drug_b = rule.get('group_b', '').strip().lower()
            severity = rule.get('severity', 5)
            remedy = rule.get('remedy', '')
            custom_factors = rule.get('custom_factors', {})

            _, created = Interaction.objects.get_or_create(
                drug_a=drug_a,
                drug_b=drug_b,
                reaction=rx_obj,
                defaults={
                    'severity_slider': severity,
                    'remedy': remedy,
                    'custom_factors': custom_factors,
                    'time_window_hours': 24
                }
            )
            if created:
                rules_count += 1

        self.stdout.write(self.style.SUCCESS(f"Seeded {rules_count} new interaction rules into SQLite!"))
