from django.core.management.base import BaseCommand
from tracker.models import Drug, Interaction, ReactionDefinition

class Command(BaseCommand):
    help = 'Inject exactly 1 test rule into PostgreSQL to verify frontend connectivity'

    def handle(self, *args, **options):
        from django.conf import settings
        db_config = settings.DATABASES['default']
        self.stdout.write(f"Connected Database Engine: {db_config['ENGINE']}")
        self.stdout.write(f"Connected Database Name: {db_config['NAME']}")

        self.stdout.write("Wiping existing database to ensure a clean slate...")
        Interaction.objects.all().delete()
        ReactionDefinition.objects.all().delete()
        Drug.objects.all().delete()

        self.stdout.write("Injecting Test Data...")
        # Create Drugs
        Drug.objects.create(name="Test Drug A")
        Drug.objects.create(name="Test Drug B")

        # Create Reaction
        rx = ReactionDefinition.objects.create(name="Severe Test Reaction")

        # Create Interaction
        Interaction.objects.create(
            drug_a="test drug a",
            drug_b="test drug b",
            reaction=rx,
            severity_slider=10,
            remedy="This is a test remedy to verify the UI.",
            organ_bitmask=1,  # 1 = Brain
            time_window_hours=24,
            custom_factors={}
        )

        self.stdout.write("✅ Successfully injected 1 test rule!")
        self.stdout.write(f"Current Drugs in DB: {Drug.objects.count()}")
        self.stdout.write(f"Current Rules in DB: {Interaction.objects.count()}")
        self.stdout.write("\nTest complete! Refresh your browser and check the Admin panel.")
