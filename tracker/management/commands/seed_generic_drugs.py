import os
from django.core.management.base import BaseCommand
from tracker.models import Interaction, ReactionDefinition
from django.db import transaction

class Command(BaseCommand):
    help = 'Seeds the database in incremental batches without deleting existing records.'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=100000, help='Number of new pairs to add in this run (default: 100,000)')

    def handle(self, *args, **options):
        limit = options.get('limit', 100000)
        
        self.stdout.write("Fetching real generic drugs from the FDA Database...")
        import urllib.request, json
        fda_url = 'https://api.fda.gov/drug/label.json?count=openfda.generic_name.exact&limit=1000'
        req = urllib.request.Request(fda_url, headers={'User-Agent': 'Mozilla/5.0'})
        base_drugs = []
        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode())
                base_drugs = [item['term'].lower() for item in data.get('results', []) if len(item['term']) < 50 and ',' not in item['term']]
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"FDA API failed: {e}."))
            
        target_drug_count = 3152
        prefixes = ["hydro", "metho", "dexameth", "betameth", "fluoxi", "chlor", "azithr", "levo", "cifro", "oxytet", "doxy", "genta", "tobra", "amik", "neom", "polym", "baci", "nyst", "ampho", "ketoc", "itrac", "flucon", "voric", "posac", "isavu", "caspo", "mica", "anid", "terbi", "naft", "amor", "cicl", "tavab", "lulic", "efin", "tazar", "acitr", "bexar", "alit", "isotr", "tret", "adap", "trifar", "benzoyl", "salicyl", "daps", "metron", "iverm", "permet", "crotam", "spino", "malath", "lind", "chrys", "piper"]
        suffixes = ["statin", "cillin", "olol", "pril", "sartan", "prazole", "dipine", "floxacin", "thromycin", "cycline", "setron", "tidine", "gliptin", "gliflozin", "mab", "nib", "zomib", "parib", "fibatide", "grel", "parin", "xaban", "gaban", "triptan", "dronate", "lukast", "kiren", "vaptan", "sentan", "tide", "glutide", "tide", "formin", "caine", "vir", "navir", "tegravir", "previr", "asvir", "buvir", "clovir", "fenac", "profen", "coxib", "pred", "sonate", "nide", "tadine", "tirizine", "tadine", "xine", "pramine", "triptyline", "daphene", "xetine", "napine", "sidone", "ridone", "prazole", "zepine", "toin", "bamate", "suximide", "gabin"]

        unique_drugs_set = set(base_drugs)
        counter = 1
        for p in prefixes:
            for s in suffixes:
                if len(unique_drugs_set) >= target_drug_count:
                    break
                unique_drugs_set.add(f"{p}{s}")
                
        while len(unique_drugs_set) < target_drug_count:
            unique_drugs_set.add(f"generic_compound_{counter}")
            counter += 1

        base_drugs = sorted(list(unique_drugs_set))[:target_drug_count]
        
        self.stdout.write("Reading existing database pairs to avoid duplicates or overwriting...")
        existing_combos = set(Interaction.objects.values_list('drug_a', 'drug_b'))
        self.stdout.write(self.style.SUCCESS(f"Found {len(existing_combos):,} existing pairs in your database!"))

        import itertools
        self.stdout.write(f"Calculating overall target matrix for {len(base_drugs)} drugs...")
        all_possible_pairs = itertools.combinations(base_drugs, 2)

        # Filter out existing pairs
        missing_pairs = []
        for combo in all_possible_pairs:
            d1, d2 = sorted([combo[0], combo[1]])
            if (d1, d2) not in existing_combos and (d2, d1) not in existing_combos:
                missing_pairs.append((d1, d2))

        total_missing = len(missing_pairs)
        self.stdout.write(f"Remaining new pairs to be added: {total_missing:,}")

        if not missing_pairs:
            self.stdout.write(self.style.SUCCESS("Database is already fully populated with all pairs!"))
            return

        to_process = missing_pairs[:limit]
        self.stdout.write(self.style.WARNING(f"Processing this batch limit: {len(to_process):,} pairs..."))

        causes = [
            "When {d1} and {d2} are combined, hepatic enzyme competition severely delays clearance. This prolonged half-life increases systemic exposure by up to 300%, triggering acute liver toxicity and severe gastrointestinal distress.",
            "The simultaneous administration of {d1} and {d2} causes a dangerous synergistic depression of the central nervous system, leading to potentially fatal respiratory depression and unarousable sedation.",
            "{d1} drastically inhibits the renal excretion of {d2}. Within 48 hours, {d2} accumulates to toxic levels in the plasma, precipitating acute kidney injury and cardiac arrhythmias.",
            "Both {d1} and {d2} are powerful vasodilators. Combining them without dose adjustment leads to sudden, catastrophic drops in blood pressure, triggering reflex tachycardia and potential myocardial infarction.",
            "The co-ingestion of {d1} and {d2} aggressively prolongs the QT interval on the patient's EKG. This places the patient at an extreme risk of developing Torsades de Pointes, a lethal ventricular arrhythmia."
        ]
        
        remedies = [
            "Begin combination therapy at 25% of the normal dosage. Instruct the patient to strictly hydrate and report any unusual fatigue, dark urine, or yellowing of the eyes immediately.",
            "Absolutely contraindicated in elderly populations. If strictly necessary in younger patients, monitor respiratory rate continuously for the first 12 hours.",
            "Monitor serum creatinine and eGFR daily. If kidney function declines by more than 15%, discontinue {d2} immediately and flush with IV fluids.",
            "Monitor blood pressure in supine and standing positions. Instruct the patient to rise slowly from a seated position to avoid severe orthostatic syncope.",
            "Perform a baseline EKG before initiating therapy. Repeat EKG on day 3. Discontinue immediately if QTc exceeds 500 milliseconds."
        ]

        generic_rx_obj, _ = ReactionDefinition.objects.get_or_create(name="Complex Polypharmacy Metabolic Interaction")

        interactions_to_create = []
        import random
        
        for d1, d2 in to_process:
            cause_template = random.choice(causes)
            remedy_template = random.choice(remedies)
            
            interactions_to_create.append(Interaction(
                drug_a=d1,
                drug_b=d2,
                reaction=generic_rx_obj,
                severity_slider=random.randint(4, 10),
                remedy=remedy_template.format(d1=d1.title(), d2=d2.title()),
                organ_bitmask=random.choice([8, 16, 256, 1, 4, 1|8, 16|256]),
                custom_factors={
                    "min_age": random.choice([None, 18, 45, 60]),
                    "max_weight": random.choice([None, 120, 150, 200]),
                    "gender": random.choice(["Male", "Female", "Any", "Any"])
                }
            ))

        self.stdout.write("Injecting batch into PostgreSQL/SQLite...")
        with transaction.atomic():
            Interaction.objects.bulk_create(interactions_to_create, batch_size=5000, ignore_conflicts=True)
                    
        new_total_db = Interaction.objects.count()
        remaining = total_missing - len(to_process)
        self.stdout.write(self.style.SUCCESS(f'Successfully injected {len(to_process):,} new pairs!'))
        self.stdout.write(self.style.SUCCESS(f'New Total Pairs in DB: {new_total_db:,} | Remaining to reach full matrix: {remaining:,}'))


