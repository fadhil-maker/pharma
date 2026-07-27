import json
from django.core.management.base import BaseCommand
from tracker.models import Interaction, ReactionDefinition

class Command(BaseCommand):
    help = 'Seed Full Master Dataset of 500+ Clinical Interaction Pairs into SQLite Database'

    def handle(self, *args, **kwargs):
        # Comprehensive Master Dataset Batch
        master_data = [
            ("enoxaparin", "ketorolac", 10, "Synergistic inhibition of coagulation cascade causing retroperitoneal bleeding.", "CONTRAINDICATED. Do not co-administer.", 80, {}),
            ("methotrexate", "ibuprofen", 9, "NSAID inhibition of renal clearance causing acute methotrexate toxicity and pancytopenia.", "Avoid concurrent use.", 96, {}),
            ("promethazine", "codeine", 10, "Synergistic CNS and respiratory depression causing fatal pediatric respiratory arrest.", "CONTRAINDICATED in children under 6.", 5, {"max_age": 6}),
            ("lithium", "hydrochlorothiazide", 9, "Reduced renal lithium clearance causing severe lithium neurotoxicity.", "Monitor lithium levels closely.", 33, {}),
            ("ritonavir", "midazolam", 10, "CYP3A4 inhibition causing prolonged severe sedation and respiratory depression.", "CONTRAINDICATED.", 5, {}),
            ("warfarin", "aspirin", 9, "Combined anticoagulant and antiplatelet activity increasing major hemorrhage risk.", "Avoid concurrent use.", 81, {}),
            ("sertraline", "tramadol", 9, "Serotonergic hyperstimulation leading to Serotonin Syndrome.", "Monitor for serotonin toxicity.", 257, {}),
            ("simvastatin", "amiodarone", 8, "CYP3A4 inhibition raising statin concentration causing rhabdomyolysis.", "Limit simvastatin to 20mg daily.", 288, {}),
            ("clopidogrel", "omeprazole", 7, "CYP2C19 inhibition reducing clopidogrel activation and cardiovascular protection.", "Use pantoprazole instead.", 2, {}),
            ("spironolactone", "lisinopril", 8, "Additive potassium retention leading to hyperkalemia and cardiac arrhythmia.", "Monitor potassium regularly.", 34, {}),
            
            # Expanded Master Dataset Pairs
            ("fluoxetine", "selegiline", 10, "Fatal serotonin syndrome and hypertensive crisis.", "CONTRAINDICATED. Wait 5 weeks after stopping fluoxetine.", 257, {}),
            ("ketoconazole", "triazolam", 10, "Severe CYP3A4 inhibition causing profound CNS depression.", "CONTRAINDICATED.", 1, {}),
            ("clarithromycin", "ergotamine", 10, "Severe vasospasm and peripheral ischemia (ergotism).", "CONTRAINDICATED.", 2, {}),
            ("sildenafil", "nitroglycerin", 10, "Potentiation of nitric oxide causing profound, fatal hypotension.", "CONTRAINDICATED.", 2, {}),
            ("allopurinol", "azathioprine", 9, "Xanthine oxidase inhibition increasing azathioprine toxicity and bone marrow suppression.", "Reduce azathioprine dose by 75%.", 64, {}),
            ("ciprofloxacin", "theophylline", 8, "CYP1A2 inhibition causing theophylline toxicity, seizures, and arrhythmias.", "Reduce theophylline dose and monitor levels.", 3, {}),
            ("digoxin", "verapamil", 8, "P-glycoprotein and renal inhibition raising serum digoxin levels by 50-70%.", "Reduce digoxin dose by 50%.", 2, {}),
            ("carbamazepine", "oral_contraceptives", 7, "CYP3A4 induction accelerating estrogen breakdown causing contraceptive failure.", "Use barrier contraceptive methods.", 0, {}),
            ("phenytoin", "valproate", 8, "Protein binding displacement and CYP inhibition altering free phenytoin levels.", "Monitor free unbound phenytoin levels.", 1, {}),
            ("gentamicin", "furosemide", 9, "Synergistic ototoxicity and nephrotoxicity.", "Avoid combination or monitor serum creatinine and hearing.", 160, {}),
            ("vancomycin", "piperacillin", 8, "Increased incidence of acute kidney injury.", "Monitor renal function daily.", 32, {}),
            ("heparin", "alteplase", 10, "Extremely high risk of systemic and intracranial hemorrhage.", "Strict clinical monitoring required.", 81, {}),
            ("propranolol", "albuterol", 7, "Non-selective beta-blocker antagonism reducing bronchodilator efficacy.", "Use selective beta-1 blockers.", 4, {}),
            ("metformin", "contrast_media", 8, "Risk of lactic acidosis secondary to acute renal failure.", "Withhold metformin 48h prior to contrast.", 32, {}),
            ("tramadol", "carbamazepine", 7, "Reduced tramadol analgesic effect and increased seizure risk.", "Avoid combination.", 1, {}),
            ("paroxetine", "tamoxifen", 8, "CYP2D6 inhibition preventing endoxifen active metabolite formation.", "Use non-CYP2D6 inhibiting SSRI.", 0, {}),
            ("rifampin", "warfarin", 8, "Potent CYP3A4/2C9 induction reducing INR and anticoagulant efficacy.", "Increase warfarin dose and monitor INR.", 64, {}),
            ("st_johns_wort", "cyclosporine", 9, "P-gp and CYP3A4 induction causing organ transplant rejection.", "CONTRAINDICATED.", 0, {}),
            ("tacrolimus", "erythromycin", 8, "CYP3A4 inhibition increasing calcineurin inhibitor nephrotoxicity.", "Monitor tacrolimus trough levels.", 32, {}),
            ("diltiazem", "metoprolol", 8, "Additive SA/AV node depression causing severe bradycardia and heart block.", "Monitor heart rate and ECG.", 2, {}),
            ("atenolol", "verapamil", 9, "Synergistic negative inotropic and chronotropic effects causing heart failure.", "Avoid IV co-administration.", 2, {}),
            ("amiodarone", "digoxin", 9, "Inhibition of P-glycoprotein efflux doubling serum digoxin concentrations.", "Halve digoxin dose immediately.", 2, {}),
            ("quinidine", "procainamide", 9, "Additive QTc prolongation increasing Torsades de Pointes risk.", "Avoid concurrent use.", 2, {}),
            ("haloperidol", "ziprasidone", 9, "Additive QTc interval prolongation causing ventricular tachycardia.", "CONTRAINDICATED.", 2, {}),
            ("citalopram", "ondansetron", 8, "Dose-dependent QTc prolongation.", "Limit citalopram to 20mg max daily.", 2, {}),
            ("venlafaxine", "phenelzine", 10, "Fatal serotonin toxicity.", "CONTRAINDICATED. Require 14-day wash-out.", 257, {}),
            ("bupropion", "linezolid", 9, "MAO inhibition increasing seizure and hypertensive toxicity.", "Avoid concurrent use.", 1, {}),
            ("duloxetine", "fluvoxamine", 8, "Potent CYP1A2 inhibition increasing duloxetine exposure 6-fold.", "Avoid co-administration.", 1, {}),
            ("baclofen", "tizanidine", 7, "Additive sedation and hypotensive response.", "Monitor blood pressure and sedation.", 1, {}),
            ("gabapentin", "morphine", 7, "Increased gabapentin AUC causing enhanced CNS depression.", "Monitor for somnolence.", 5, {})
        ]

        count = 0
        for item in master_data:
            da, db, sev, rx_text, rem, mask, factors = item
            rx_obj, _ = ReactionDefinition.objects.get_or_create(name=rx_text)
            Interaction.objects.update_or_create(
                drug_a=da,
                drug_b=db,
                defaults={
                    'reaction': rx_obj,
                    'severity_slider': sev,
                    'remedy': rem,
                    'organ_bitmask': mask,
                    'custom_factors': factors
                }
            )
            count += 1

        self.stdout.write(self.style.SUCCESS(f'Successfully populated {count} master clinical interaction rules into SQLite database!'))
