from django.core.management.base import BaseCommand
from tracker.models import Interaction
from django.db.models import Q

class Command(BaseCommand):
    help = 'Injects perfectly accurate clinical data into existing database pairs.'

    def handle(self, *args, **options):
        # A curated list of real, highly dangerous clinical interactions
        real_data = [
            {
                "drug_a": "warfarin", "drug_b": "aspirin",
                "severity": 10,
                "cause": "Aspirin permanently inhibits platelet cyclooxygenase (COX-1), while Warfarin depletes Vitamin K-dependent clotting factors. Combined, they drastically eliminate both primary and secondary hemostasis, leading to severe, potentially fatal gastrointestinal or intracranial hemorrhage.",
                "remedy": "Absolute contraindication unless specifically directed by a cardiologist for severe cardiovascular disease. If prescribed, monitor INR daily and monitor for melena or unusual bruising."
            },
            {
                "drug_a": "sildenafil", "drug_b": "isosorbide",
                "severity": 10,
                "cause": "Both drugs dramatically increase intracellular cGMP in vascular smooth muscle. The synergistic vasodilation causes an abrupt, catastrophic drop in systemic blood pressure leading to cardiogenic shock or myocardial infarction.",
                "remedy": "Absolute contraindication. Nitrates must be withheld for at least 24 hours (or 48 hours for tadalafil) after PDE-5 inhibitor use. In emergency angina, use non-nitrate alternatives."
            },
            {
                "drug_a": "simvastatin", "drug_b": "amiodarone",
                "severity": 8,
                "cause": "Amiodarone is a potent inhibitor of the CYP3A4 hepatic enzyme, which is responsible for clearing simvastatin. This causes simvastatin plasma levels to spike, leading to severe skeletal muscle breakdown (rhabdomyolysis) and acute renal failure.",
                "remedy": "Limit simvastatin dose to a maximum of 20mg daily when taken with amiodarone. Instruct patient to report unexplained muscle pain or dark urine immediately."
            },
            {
                "drug_a": "lithium", "drug_b": "ibuprofen",
                "severity": 7,
                "cause": "Ibuprofen and other NSAIDs reduce renal prostaglandin synthesis, which subsequently decreases renal blood flow. This prevents the kidneys from excreting lithium, causing lithium toxicity (tremors, confusion, seizures).",
                "remedy": "Avoid NSAIDs in patients on lithium. Use acetaminophen for analgesia instead. If NSAIDs are strictly required, monitor serum lithium levels closely and reduce lithium dose."
            },
            {
                "drug_a": "albuterol", "drug_b": "propranolol",
                "severity": 8,
                "cause": "Propranolol is a non-selective beta-blocker that antagonizes the beta-2 receptors in the lungs. This completely blocks the bronchodilating effect of albuterol and can trigger severe, life-threatening bronchospasm in asthmatic patients.",
                "remedy": "Absolute contraindication in asthmatics. If a beta-blocker is required for cardiovascular reasons, use a cardioselective agent like metoprolol instead."
            },
            {
                "drug_a": "clopidogrel", "drug_b": "omeprazole",
                "severity": 7,
                "cause": "Omeprazole strongly inhibits the CYP2C19 enzyme. Clopidogrel is a prodrug that requires CYP2C19 to convert into its active metabolite. This combination renders clopidogrel useless, leading to a high risk of stent thrombosis or stroke.",
                "remedy": "Avoid omeprazole. If a PPI is required for gastric protection, prescribe pantoprazole, which does not significantly inhibit CYP2C19."
            },
            {
                "drug_a": "spironolactone", "drug_b": "lisinopril",
                "severity": 8,
                "cause": "Lisinopril (an ACE inhibitor) reduces aldosterone secretion, while spironolactone directly blocks aldosterone receptors. Both mechanisms independently cause the body to retain potassium, leading to life-threatening hyperkalemia and cardiac arrest.",
                "remedy": "Monitor serum potassium and renal function (eGFR) closely, particularly in the elderly. Limit spironolactone to 25mg daily when combined with ACE inhibitors."
            },
            {
                "drug_a": "citalopram", "drug_b": "tramadol",
                "severity": 9,
                "cause": "Both drugs significantly increase serotonin levels in the central nervous system. Co-administration can trigger Serotonin Syndrome, characterized by hyperthermia, rigid muscles, autonomic instability, and seizures.",
                "remedy": "Avoid combination if possible. If required, start tramadol at the lowest possible dose and educate the patient on the signs of serotonin toxicity."
            },
            {
                "drug_a": "methotrexate", "drug_b": "sulfamethoxazole",
                "severity": 9,
                "cause": "Sulfamethoxazole displaces methotrexate from plasma proteins and inhibits its renal excretion. This triggers acute, severe methotrexate toxicity resulting in bone marrow suppression, pancytopenia, and fatal infections.",
                "remedy": "Absolute contraindication. Use an alternative antibiotic for infections in patients taking methotrexate."
            },
            {
                "drug_a": "digoxin", "drug_b": "clarithromycin",
                "severity": 8,
                "cause": "Clarithromycin inhibits P-glycoprotein efflux transporters in the gut and kidneys. This vastly increases the absorption and decreases the excretion of digoxin, leading to severe digoxin toxicity (nausea, visual halos, fatal arrhythmias).",
                "remedy": "Reduce digoxin dose by 50% when initiating clarithromycin. Monitor serum digoxin levels and EKG continuously."
            }
        ]

        self.stdout.write(self.style.WARNING("Applying real clinical data to specific drug pairs..."))

        from tracker.models import ReactionDefinition
        reaction_obj, _ = ReactionDefinition.objects.get_or_create(name="Verified Clinical Reaction")

        updated_count = 0
        created_count = 0
        for data in real_data:
            # Find the existing dummy interaction row
            interaction = Interaction.objects.filter(
                Q(drug_a=data['drug_a'], drug_b=data['drug_b']) | 
                Q(drug_a=data['drug_b'], drug_b=data['drug_a'])
            ).first()

            if interaction:
                rx_obj, _ = ReactionDefinition.objects.get_or_create(name=data['cause'][:499])
                interaction.reaction = rx_obj
                interaction.severity_slider = data['severity']
                interaction.remedy = data['remedy']
                interaction.custom_factors = {} 
                interaction.time_window_hours = 24
                interaction.save()
                updated_count += 1
                self.stdout.write(self.style.SUCCESS(f"✅ Updated existing pair: {data['drug_a'].title()} + {data['drug_b'].title()}"))
            else:
                # The FDA base list didn't include these specific drugs, so we will forcibly create them!
                rx_obj, _ = ReactionDefinition.objects.get_or_create(name=data['cause'][:499])
                Interaction.objects.create(
                    drug_a=data['drug_a'],
                    drug_b=data['drug_b'],
                    reaction=rx_obj,
                    severity_slider=data['severity'],
                    remedy=data['remedy'],
                    custom_factors={},
                    time_window_hours=24
                )
                created_count += 1
                self.stdout.write(self.style.WARNING(f"✨ Forcibly added missing drugs to DB: {data['drug_a'].title()} + {data['drug_b'].title()}"))

        self.stdout.write(self.style.SUCCESS(f"\n🎉 Successfully injected {updated_count + created_count} real-world clinical pairs!"))
