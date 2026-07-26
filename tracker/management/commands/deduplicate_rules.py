from django.core.management.base import BaseCommand
from tracker.models import Interaction

class Command(BaseCommand):
    help = 'Finds and purges duplicate/near-duplicate drug interaction rules, keeping the highest severity / most detailed version.'

    def handle(self, *args, **options):
        def clean_name(name):
            name = name.strip().lower()
            if name.startswith('@'):
                name = name[1:]
            return name

        rules = list(Interaction.objects.all())
        total_before = len(rules)
        
        seen_pairs = {}
        to_delete = []

        # Prefer keeping rule with @ tag in drug name if severity is equal, then longest reaction text
        for r in sorted(rules, key=lambda x: (x.severity_slider, 1 if ('@' in x.drug_a or '@' in x.drug_b) else 0, len(str(x.reaction.name if x.reaction else ''))), reverse=True):
            norm_a = clean_name(r.drug_a)
            norm_b = clean_name(r.drug_b)
            pair_key = tuple(sorted([norm_a, norm_b]))

            if pair_key in seen_pairs:
                to_delete.append(r)
            else:
                seen_pairs[pair_key] = r

        delete_ids = [r.id for r in to_delete]
        if delete_ids:
            purged_count = Interaction.objects.filter(id__in=delete_ids).delete()[0]
            self.stdout.write(self.style.SUCCESS(f"Successfully purged {purged_count} duplicate interaction rule(s) (including @ tag duplicates) from database!"))
        else:
            self.stdout.write(self.style.SUCCESS("No duplicate rules found in database."))

        self.stdout.write(self.style.SUCCESS(f"Total Rules: {total_before} -> {Interaction.objects.count()} clean unique rules remaining."))
