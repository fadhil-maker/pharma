from django.core.management.base import BaseCommand
from tracker.models import Interaction, ReactionDefinition

class Command(BaseCommand):
    help = 'Seed Master Clinical Dataset into Database'

    def handle(self, *args, **kwargs):
        rules = [
            {
                'drug_a': 'enoxaparin', 'drug_b': 'ketorolac', 'severity': 10,
                'reaction': 'Synergistic inhibition of coagulation cascade and platelet aggregation causing massive retroperitoneal and gastrointestinal bleeding.',
                'remedy': 'CONTRAINDICATED. Do not co-administer NSAIDs with low molecular weight heparin.',
                'organ_bitmask': 80, # GI (16) + Blood (64)
                'custom_factors': {}
            },
            {
                'drug_a': 'methotrexate', 'drug_b': 'ibuprofen', 'severity': 9,
                'reaction': 'NSAID inhibition of renal prostaglandin clearance causing acute methotrexate toxicity, bone marrow suppression, and pancytopenia.',
                'remedy': 'Avoid high-dose methotrexate co-administration with NSAIDs. Monitor blood counts.',
                'organ_bitmask': 96, # GI (16) + Kidneys (32) + Blood (64)
                'custom_factors': {}
            },
            {
                'drug_a': 'promethazine', 'drug_b': 'codeine', 'severity': 10,
                'reaction': 'Synergistic CNS and respiratory depression causing fatal pediatric respiratory arrest.',
                'remedy': 'CONTRAINDICATED in children under 6 years of age.',
                'organ_bitmask': 5, # Brain (1) + Lungs (4)
                'custom_factors': {'max_age': 6}
            },
            {
                'drug_a': 'lithium', 'drug_b': 'hydrochlorothiazide', 'severity': 9,
                'reaction': 'Reduced renal lithium clearance causing severe lithium neurotoxicity, tremors, and confusion.',
                'remedy': 'Monitor serum lithium levels closely and reduce lithium dosage by 25-50%.',
                'organ_bitmask': 33, # Brain (1) + Kidneys (32)
                'custom_factors': {}
            },
            {
                'drug_a': 'ritonavir', 'drug_b': 'midazolam', 'severity': 10,
                'reaction': 'Extreme CYP3A4 inhibition causing prolonged, severe sedation and life-threatening respiratory depression.',
                'remedy': 'CONTRAINDICATED. Use alternative non-CYP3A4 metabolized sedatives.',
                'organ_bitmask': 5, # Brain (1) + Lungs (4)
                'custom_factors': {}
            },
            {
                'drug_a': 'warfarin', 'drug_b': 'aspirin', 'severity': 9,
                'reaction': 'Combined anticoagulant and antiplatelet activity dramatically increasing risk of major gastrointestinal and intracranial hemorrhage.',
                'remedy': 'Avoid concurrent use unless specifically indicated for cardiac prosthetic valves.',
                'organ_bitmask': 81, # Brain (1) + GI (16) + Blood (64)
                'custom_factors': {}
            },
            {
                'drug_a': 'sertraline', 'drug_b': 'tramadol', 'severity': 9,
                'reaction': 'Serotonergic hyperstimulation leading to Serotonin Syndrome (hyperthermia, myoclonus, autonomic instability).',
                'remedy': 'Monitor closely for symptoms of serotonin toxicity or use alternative analgesics.',
                'organ_bitmask': 257, # Brain (1) + Muscles (256)
                'custom_factors': {}
            },
            {
                'drug_a': 'simvastatin', 'drug_b': 'amiodarone', 'severity': 8,
                'reaction': 'CYP3A4 inhibition raising statin concentration leading to severe rhabdomyolysis and myopathy.',
                'remedy': 'Limit simvastatin dose to maximum 20mg daily when combined with amiodarone.',
                'organ_bitmask': 288, # Kidneys (32) + Muscles (256)
                'custom_factors': {}
            },
            {
                'drug_a': 'clopidogrel', 'drug_b': 'omeprazole', 'severity': 7,
                'reaction': 'CYP2C19 inhibition reducing activation of clopidogrel, increasing adverse cardiovascular ischemic events.',
                'remedy': 'Use non-CYP2C19 inhibiting PPIs like pantoprazole.',
                'organ_bitmask': 2, # Heart (2)
                'custom_factors': {}
            },
            {
                'drug_a': 'spironolactone', 'drug_b': 'lisinopril', 'severity': 8,
                'reaction': 'Additive potassium retention leading to severe hyperkalemia and cardiac arrhythmia.',
                'remedy': 'Monitor serum potassium levels regularly, especially in renal impairment.',
                'organ_bitmask': 34, # Heart (2) + Kidneys (32)
                'custom_factors': {}
            }
        ]

        added = 0
        for r in rules:
            rx, _ = ReactionDefinition.objects.get_or_create(name=r['reaction'])
            Interaction.objects.update_or_create(
                drug_a=r['drug_a'],
                drug_b=r['drug_b'],
                defaults={
                    'reaction': rx,
                    'severity_slider': r['severity'],
                    'remedy': r['remedy'],
                    'organ_bitmask': r['organ_bitmask'],
                    'custom_factors': r['custom_factors']
                }
            )
            added += 1

        self.stdout.write(self.style.SUCCESS(f'Successfully seeded {added} master clinical dataset rules into database!'))
