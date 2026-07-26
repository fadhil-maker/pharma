from django.core.management.base import BaseCommand
from tracker.models import Interaction

class Command(BaseCommand):
    help = 'Finds and purges duplicate/near-duplicate drug interaction rules, keeping the highest severity / most detailed version.'

    def handle(self, *args, **options):
        rules = list(Interaction.objects.all())
        total_before = len(rules)
        
        seen_pairs = {}
        to_delete = []

        # Sort by highest severity index first, then longest reaction description
        for r in sorted(rules, key=lambda x: (x.severity_slider, len(str(x.reaction.name if x.reaction else ''))), reverse=True):
            pair = tuple(sorted([r.drug_a.strip().lower(), r.drug_b.strip().lower()]))
            if pair in seen_pairs:
                to_delete.append(r)
            else:
                seen_pairs[pair] = r

        delete_ids = [r.id for r in to_delete]
        if delete_ids:
            purged_count = Interaction.objects.filter(id__in=delete_ids).delete()[0]
            self.stdout.write(self.style.SUCCESS(f"✅ Successfully purged {purged_count} duplicate interaction rule(s) from database!"))
        else:
            self.stdout.write(self.style.SUCCESS("✨ No duplicate rules found in database."))

        self.stdout.write(self.style.SUCCESS(f"Total Rules: {total_before} → {Interaction.objects.count()} clean unique rules remaining."))
