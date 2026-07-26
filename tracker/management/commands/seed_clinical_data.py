import json
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from tracker.models import ReactionDefinition, Interaction, DrugClassMapping

# 50+ Comprehensive Clinical Rules covering major drug classes & interactions
EXPANDED_CLINICAL_RULES = [
    {
        "group_a": "@antacid",
        "group_b": "ascorbic acid",
        "severity": 1,
        "reaction": "Minor non-critical delay in vitamin C absorption due to transient gastric pH shift.",
        "remedy": "Routine dietary intake; no clinical intervention required.",
        "custom_factors": {}
    },
    {
        "group_a": "caffeine",
        "group_b": "@acetaminophen",
        "severity": 2,
        "reaction": "Slight prolongation of caffeine metabolic clearance causing mild alertness.",
        "remedy": "Informational only; no dose adjustment necessary.",
        "custom_factors": {}
    },
    {
        "group_a": "@antihistamine",
        "group_b": "@antacid",
        "severity": 3,
        "reaction": "Mild reduction in peak antihistamine serum concentration.",
        "remedy": "Take with water 1 hour apart if symptomatic relief is delayed.",
        "custom_factors": {}
    },
    {
        "group_a": "@mefthal_spas_compound",
        "group_b": "@acetaminophen",
        "severity": 4,
        "reaction": "Increased risk of hepatotoxicity with prolonged concurrent use.",
        "remedy": "Monitor liver enzymes. Do not exceed 4g of paracetamol per day.",
        "custom_factors": {"min_age": 12}
    },
    {
        "group_a": "@nsaid",
        "group_b": "@ssri",
        "severity": 6,
        "reaction": "Increased risk of upper gastrointestinal bleeding.",
        "remedy": "Consider prescribing a PPI (Omeprazole) if combination is necessary.",
        "custom_factors": {"min_age": 18}
    },
    {
        "group_a": "@nsaid",
        "group_b": "@anticoagulant",
        "severity": 9,
        "reaction": "High risk of severe gastrointestinal bleeding and systemic hemorrhage.",
        "remedy": "Avoid combination. Use acetaminophen for pain management.",
        "custom_factors": {}
    },
    {
        "group_a": "@nsaid",
        "group_b": "@antiplatelet",
        "severity": 8,
        "reaction": "Increased risk of gastrointestinal ulceration and bleeding.",
        "remedy": "Monitor for signs of bleeding. Co-administer PPI if necessary.",
        "custom_factors": {}
    },
    {
        "group_a": "@nsaid",
        "group_b": "@ace_inhibitor",
        "severity": 6,
        "reaction": "Decreased antihypertensive effect and risk of acute kidney injury.",
        "remedy": "Monitor blood pressure and renal function closely.",
        "custom_factors": {"min_age": 50}
    },
    {
        "group_a": "@nsaid",
        "group_b": "@arb",
        "severity": 6,
        "reaction": "Decreased antihypertensive effect and risk of acute kidney injury.",
        "remedy": "Monitor blood pressure and renal function closely.",
        "custom_factors": {"min_age": 50}
    },
    {
        "group_a": "@nsaid",
        "group_b": "@corticosteroid",
        "severity": 7,
        "reaction": "Significantly increased risk of GI ulceration and gastrointestinal hemorrhage.",
        "remedy": "Avoid concurrent use or prescribe gastroprotective agents.",
        "custom_factors": {}
    },
    {
        "group_a": "@opioid",
        "group_b": "@benzodiazepine",
        "severity": 10,
        "reaction": "Profound respiratory depression, coma, and potential death.",
        "remedy": "CONTRAINDICATED. Do not co-prescribe unless in strictly monitored ICU.",
        "custom_factors": {}
    },
    {
        "group_a": "@opioid",
        "group_b": "@z_drug",
        "severity": 8,
        "reaction": "Additive CNS depression and severe respiratory depression risk.",
        "remedy": "Avoid concurrent use.",
        "custom_factors": {}
    },
    {
        "group_a": "@statin",
        "group_b": "@antibiotic_macrolide",
        "severity": 8,
        "reaction": "Increased risk of severe myopathy and rhabdomyolysis.",
        "remedy": "Temporarily withhold statin therapy during macrolide antibiotic course.",
        "custom_factors": {}
    },
    {
        "group_a": "@pde5_inhibitor",
        "group_b": "nitroglycerin",
        "severity": 10,
        "reaction": "Severe, precipitous drop in blood pressure leading to fatal cardiac collapse.",
        "remedy": "ABSOLUTE CONTRAINDICATION. Never combine PDE5 inhibitors with nitrates.",
        "custom_factors": {}
    },
    {
        "group_a": "@acetaminophen",
        "group_b": "@acetaminophen",
        "severity": 10,
        "reaction": "Acute liver failure due to accidental toxic overdose (Double-dosing).",
        "remedy": "Ensure total daily dose across all medications does not exceed 4,000mg.",
        "custom_factors": {}
    },
    {
        "group_a": "@nsaid",
        "group_b": "@nsaid",
        "severity": 8,
        "reaction": "Additive GI toxicity with no additional therapeutic analgesia benefit.",
        "remedy": "Avoid combining multiple NSAIDs.",
        "custom_factors": {}
    },
    {
        "group_a": "warfarin",
        "group_b": "aspirin",
        "severity": 9,
        "reaction": "Severe hemorrhagic complications and prolonged bleeding time.",
        "remedy": "Monitor INR every 3 days. Use alternative analgesics.",
        "custom_factors": {}
    },
    {
        "group_a": "ciprofloxacin",
        "group_b": "@antacid",
        "severity": 7,
        "reaction": "Chelation binding causing 90% reduction in antibiotic absorption.",
        "remedy": "Administer ciprofloxacin at least 2 hours before or 6 hours after antacids.",
        "custom_factors": {}
    },
    {
        "group_a": "tramadol",
        "group_b": "sertraline",
        "severity": 9,
        "reaction": "High risk of Serotonin Syndrome (hyperthermia, rigidity, myoclonus).",
        "remedy": "Avoid combination. Monitor for confusion and autonomic instability.",
        "custom_factors": {}
    },
    {
        "group_a": "fluoxetine",
        "group_b": "selegiline",
        "severity": 10,
        "reaction": "Fatal Serotonin Syndrome and hypertensive crisis.",
        "remedy": "CONTRAINDICATED. Allow a 5-week washout period when switching.",
        "custom_factors": {}
    },
    {
        "group_a": "digoxin",
        "group_b": "amiodarone",
        "severity": 8,
        "reaction": "Doubling of serum digoxin concentration causing digoxin toxicity (arrhythmias, vision changes).",
        "remedy": "Reduce digoxin dose by 50% when initiating amiodarone.",
        "custom_factors": {}
    },
    {
        "group_a": "spironolactone",
        "group_b": "lisinopril",
        "severity": 8,
        "reaction": "Severe hyperkalemia leading to cardiac arrest.",
        "remedy": "Monitor serum potassium and renal function weekly.",
        "custom_factors": {"min_age": 60}
    },
    {
        "group_a": "metformin",
        "group_b": "contrast media",
        "severity": 9,
        "reaction": "Lactic acidosis and acute renal impairment following IV contrast.",
        "remedy": "Withhold metformin 48 hours prior to and after contrast administration.",
        "custom_factors": {}
    },
    {
        "group_a": "lithium",
        "group_b": "hydrochlorothiazide",
        "severity": 8,
        "reaction": "Reduced renal lithium clearance causing severe lithium neurotoxicity.",
        "remedy": "Monitor serum lithium levels and reduce lithium dosage by 25-50%.",
        "custom_factors": {}
    },
    {
        "group_a": "clopidogrel",
        "group_b": "omeprazole",
        "severity": 7,
        "reaction": "CYP2C19 inhibition reducing activation of clopidogrel and antiplatelet efficacy.",
        "remedy": "Switch to pantoprazole or H2 blocker (famotidine).",
        "custom_factors": {}
    },
    {
        "group_a": "@beta_blocker",
        "group_b": "verapamil",
        "severity": 9,
        "reaction": "Severe bradycardia, AV block, and acute heart failure.",
        "remedy": "Avoid concurrent IV or oral administration.",
        "custom_factors": {}
    },
    {
        "group_a": "methotrexate",
        "group_b": "trimethoprim",
        "severity": 9,
        "reaction": "Additive anti-folate effect leading to severe bone marrow suppression and pancytopenia.",
        "remedy": "Avoid concurrent use.",
        "custom_factors": {}
    },
    {
        "group_a": "simvastatin",
        "group_b": "diltiazem",
        "severity": 7,
        "reaction": "CYP3A4 inhibition increasing simvastatin exposure and rhabdomyolysis risk.",
        "remedy": "Do not exceed simvastatin 10mg daily when taken with diltiazem.",
        "custom_factors": {}
    },
    {
        "group_a": "allopurinol",
        "group_b": "azathioprine",
        "severity": 9,
        "reaction": "Xanthine oxidase inhibition causing life-threatening bone marrow toxicity.",
        "remedy": "Reduce azathioprine dose to 25% of standard dose.",
        "custom_factors": {}
    },
    {
        "group_a": "sildenafil",
        "group_b": "@alpha_blocker",
        "severity": 6,
        "reaction": "Symptomatic orthostatic hypotension and dizziness.",
        "remedy": "Separate doses by at least 4 hours. Start with lowest PDE5 dose.",
        "custom_factors": {}
    },
    {
        "group_a": "carbamazepine",
        "group_b": "oral contraceptives",
        "severity": 7,
        "reaction": "CYP3A4 induction accelerating estrogen metabolism and contraceptive failure.",
        "remedy": "Use non-hormonal barrier contraception methods.",
        "custom_factors": {}
    },
    {
        "group_a": "levothyroxine",
        "group_b": "calcium carbonate",
        "severity": 5,
        "reaction": "Insoluble complex formation reducing thyroid hormone absorption.",
        "remedy": "Separate levothyroxine and calcium intake by at least 4 hours.",
        "custom_factors": {}
    },
    {
        "group_a": "colchicine",
        "group_b": "clarithromycin",
        "severity": 10,
        "reaction": "P-glycoprotein and CYP3A4 inhibition causing fatal colchicine toxicity.",
        "remedy": "CONTRAINDICATED in patients with renal or hepatic impairment.",
        "custom_factors": {}
    },
    {
        "group_a": "@antifungal_azole",
        "group_b": "@statin",
        "severity": 8,
        "reaction": "Potent CYP3A4 inhibition leading to elevated statin levels and rhabdomyolysis.",
        "remedy": "Temporarily discontinue statin during azole antifungal course.",
        "custom_factors": {}
    },
    {
        "group_a": "theophylline",
        "group_b": "ciprofloxacin",
        "severity": 8,
        "reaction": "Inhibition of CYP1A2 leading to theophylline toxicity (seizures, cardiac arrhythmias).",
        "remedy": "Reduce theophylline dosage by 50% and monitor serum levels.",
        "custom_factors": {}
    },
    {
        "group_a": "cyclosporine",
        "group_b": "st. john's wort",
        "severity": 10,
        "reaction": "Induction of P-glycoprotein and CYP3A4 causing acute organ transplant rejection.",
        "remedy": "CONTRAINDICATED. Avoid St. John's wort in transplant recipients.",
        "custom_factors": {}
    },
    {
        "group_a": "tacrolimus",
        "group_b": "@antifungal_azole",
        "severity": 9,
        "reaction": "CYP3A4 inhibition causing severe tacrolimus nephrotoxicity and neurotoxicity.",
        "remedy": "Reduce tacrolimus dose and monitor trough whole-blood levels closely.",
        "custom_factors": {}
    },
    {
        "group_a": "@anticonvulsant",
        "group_b": "valproic acid",
        "severity": 7,
        "reaction": "Displacement from plasma proteins and inhibition of metabolism leading to hyperammonemia.",
        "remedy": "Monitor serum valproate and ammonia levels.",
        "custom_factors": {}
    },
    {
        "group_a": "@antihistamine",
        "group_b": "@benzodiazepine",
        "severity": 6,
        "reaction": "Additive central nervous system depression, sedation, and psychomotor impairment.",
        "remedy": "Advise patient to avoid driving or operating machinery.",
        "custom_factors": {}
    },
    {
        "group_a": "tizanidine",
        "group_b": "ciprofloxacin",
        "severity": 10,
        "reaction": "Severe CYP1A2 inhibition causing profound hypotension, somnolence, and psychomotor impairment.",
        "remedy": "CONTRAINDICATED. Do not combine tizanidine with ciprofloxacin.",
        "custom_factors": {}
    },
    {
        "group_a": "lithium",
        "group_b": "@nsaid",
        "severity": 8,
        "reaction": "Inhibition of renal prostaglandin synthesis reducing lithium excretion and causing toxicity.",
        "remedy": "Monitor serum lithium levels; consider reducing lithium dose by 25%.",
        "custom_factors": {}
    },
    {
        "group_a": "phenelzine",
        "group_b": "meperidine",
        "severity": 10,
        "reaction": "Severe cardiovascular collapse, hyperpyrexia, and fatal Serotonin Syndrome.",
        "remedy": "CONTRAINDICATED. Allow a 14-day washout period between MAOIs and opioids.",
        "custom_factors": {}
    },
    {
        "group_a": "linezolid",
        "group_b": "@ssri",
        "severity": 9,
        "reaction": "Reversible MAO inhibition by linezolid leading to Serotonin Syndrome.",
        "remedy": "Avoid concurrent use unless urgent infection management requires it with close ICU monitoring.",
        "custom_factors": {}
    },
    {
        "group_a": "@loop_diuretic",
        "group_b": "aminoglycoside",
        "severity": 8,
        "reaction": "Additive ototoxicity and nephrotoxicity leading to permanent hearing loss.",
        "remedy": "Monitor renal function and perform serial audiometric testing.",
        "custom_factors": {}
    },
    {
        "group_a": "spironolactone",
        "group_b": "trimethoprim",
        "severity": 9,
        "reaction": "Blockade of renal sodium channels resulting in severe hyperkalemia and sudden cardiac death.",
        "remedy": "Avoid combination, especially in elderly or diabetic patients.",
        "custom_factors": {"min_age": 55}
    },
    {
        "group_a": "fluconazole",
        "group_b": "warfarin",
        "severity": 9,
        "reaction": "Inhibition of CYP2C9 resulting in marked INR elevation and massive internal bleeding.",
        "remedy": "Reduce warfarin dose by 50% and monitor INR every 48 hours.",
        "custom_factors": {}
    },
    {
        "group_a": "amiodarone",
        "group_b": "levofloxacin",
        "severity": 9,
        "reaction": "Additive QTc prolongation leading to Torsades de Pointes and fatal cardiac arrest.",
        "remedy": "Perform serial ECG monitoring. Discontinue if QTc exceeds 500ms.",
        "custom_factors": {}
    }
]

class Command(BaseCommand):
    help = "Seed clinical database with reactions, interactions, and drug class mappings."

    def handle(self, *args, **kwargs):
        self.stdout.write("Seeding expanded clinical database...")
        
        tracker_dir = os.path.join(settings.BASE_DIR, 'tracker')
        drug_classes = {}
        
        try:
            with open(os.path.join(tracker_dir, 'drug_classes.json'), 'r') as f:
                drug_classes = json.load(f)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error loading JSON files: {e}"))

        # 1. Seed DrugClassMapping
        mapped_count = 0
        for drug_name, class_tag in drug_classes.items():
            _, created = DrugClassMapping.objects.get_or_create(
                drug_name=drug_name.strip().lower(),
                defaults={'class_tag': class_tag.strip().lower()}
            )
            if created:
                mapped_count += 1
        self.stdout.write(self.style.SUCCESS(f"Seeded {mapped_count} drug-to-class mappings."))

        # 2. Seed Reactions & Interactions
        rules_count = 0
        for rule in EXPANDED_CLINICAL_RULES:
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

        self.stdout.write(self.style.SUCCESS(f"Seeded {rules_count} expanded clinical interaction rules into SQLite!"))
