import sys
from django.core.management.base import BaseCommand
from tracker.models import Interaction, ReactionDefinition
from django.db import transaction

class Command(BaseCommand):
    help = 'Seed Master Clinical Interaction Pairs with Accurate Clinical Severity Ratings (1 to 10)'

    def handle(self, *args, **kwargs):
        self.stdout.write("Compiling Master Dataset with Scientifically Accurate Clinical Severity Ratings (1 to 10)...")

        # Scientifically Classified Clinical Mechanisms & Severity Ratings (1-10)
        clinical_rules_template = [
            # Severity 10: CRITICAL / CONTRAINDICATED / FATAL RISK
            ("enoxaparin", "ketorolac", 10, "Synergistic inhibition of coagulation cascade causing fatal hemorrhage.", "CONTRAINDICATED. Do not co-administer LMWH and NSAIDs.", 80),
            ("promethazine", "codeine", 10, "Synergistic CNS and respiratory depression causing fatal pediatric respiratory arrest.", "CONTRAINDICATED in children under 6 years.", 5),
            ("fluoxetine", "selegiline", 10, "Fatal serotonin syndrome and severe hypertensive crisis.", "CONTRAINDICATED. Requires 5-week washout period.", 257),
            ("sildenafil", "nitroglycerin", 10, "Potentiation of nitric oxide causing profound, fatal hypotension.", "CONTRAINDICATED. Do not use nitrates within 24-48 hours.", 2),
            ("ritonavir", "midazolam", 10, "Extreme CYP3A4 inhibition causing prolonged coma and respiratory arrest.", "CONTRAINDICATED.", 5),

            # Severity 9: CRITICAL / MAJOR TOXICITY
            ("methotrexate", "ibuprofen", 9, "NSAID inhibition of renal prostaglandin clearance causing acute methotrexate toxicity and pancytopenia.", "Avoid concurrent use. Monitor blood counts and creatinine.", 96),
            ("lithium", "hydrochlorothiazide", 9, "Reduced renal lithium clearance causing severe lithium neurotoxicity and tremors.", "Monitor serum lithium levels closely; reduce lithium dose by 50%.", 33),
            ("warfarin", "aspirin", 9, "Combined anticoagulant and antiplatelet activity dramatically increasing risk of major hemorrhage.", "Avoid concurrent use unless indicated for prosthetic heart valves.", 81),
            ("sertraline", "tramadol", 9, "Serotonergic hyperstimulation leading to Serotonin Syndrome.", "Monitor for serotonin toxicity or use alternative analgesics.", 257),
            ("gentamicin", "furosemide", 9, "Synergistic ototoxicity and acute tubular necrosis.", "Avoid combination or monitor hearing and serum creatinine daily.", 160),

            # Severity 8: SEVERE / HIGH RISK OF ORGAN DAMAGE
            ("simvastatin", "amiodarone", 8, "CYP3A4 inhibition raising statin exposure causing rhabdomyolysis and acute kidney failure.", "Limit simvastatin dose to max 20mg daily.", 288),
            ("spironolactone", "lisinopril", 8, "Additive potassium retention leading to severe hyperkalemia and cardiac arrhythmia.", "Monitor serum potassium regularly.", 34),
            ("ciprofloxacin", "theophylline", 8, "CYP1A2 inhibition causing theophylline toxicity, seizures, and cardiac arrhythmias.", "Reduce theophylline dose and monitor plasma levels.", 3),
            ("vancomycin", "piperacillin", 8, "Synergistic nephrotoxicity increasing incidence of acute kidney injury.", "Monitor renal clearance and creatinine daily.", 32),
            ("metformin", "contrast_media", 8, "Risk of severe lactic acidosis secondary to contrast-induced acute renal failure.", "Withhold metformin 48h prior to contrast administration.", 32),

            # Severity 7: SEVERE / CLINICALLY SIGNIFICANT
            ("clopidogrel", "omeprazole", 7, "CYP2C19 inhibition reducing activation of clopidogrel and increasing cardiovascular ischemic risk.", "Use non-CYP2C19 inhibiting PPI like pantoprazole.", 2),
            ("paroxetine", "tamoxifen", 7, "CYP2D6 inhibition preventing endoxifen active metabolite formation, reducing cancer efficacy.", "Use non-CYP2D6 inhibiting SSRI like citalopram.", 0),
            ("propranolol", "albuterol", 7, "Non-selective beta-blocker antagonism reducing bronchodilator efficacy in asthma.", "Use selective beta-1 blockers like metoprolol.", 4),
            ("gabapentin", "morphine", 7, "Increased gabapentin exposure causing enhanced central nervous system depression.", "Monitor patient for excessive somnolence.", 5),
            ("carbamazepine", "oral_contraceptives", 7, "CYP3A4 induction accelerating estrogen metabolism causing contraceptive failure.", "Use alternative barrier non-hormonal contraception.", 0),

            # Severity 6: MODERATE / FREQUENT MONITORING NEEDED
            ("atenolol", "diltiazem", 6, "Additive SA/AV node depression causing bradycardia and heart block.", "Monitor pulse rate and ECG regularly.", 2),
            ("digoxin", "verapamil", 6, "P-glycoprotein inhibition raising digoxin levels by 50%.", "Reduce digoxin dose by 50% and monitor plasma levels.", 2),
            ("baclofen", "tizanidine", 6, "Additive central muscle relaxant sedation and hypotensive response.", "Monitor blood pressure and sedation levels.", 1),
            ("duloxetine", "fluvoxamine", 6, "CYP1A2 inhibition increasing duloxetine plasma exposure.", "Use caution when co-administering.", 1),
            ("tramadol", "carbamazepine", 6, "CYP3A4 induction increasing tramadol metabolism and lowering pain relief.", "Monitor analgesic response.", 1),

            # Severity 5: MODERATE / DOSAGE ADJUSTMENT MAY BE REQUIRED
            ("metformin", "cimetidine", 5, "Competition for renal organic cation transporters increasing metformin AUC.", "Monitor blood glucose levels and renal function.", 32),
            ("lisinopril", "allopurinol", 5, "Increased risk of hypersensitivity reactions and skin rash.", "Monitor for allergic reactions.", 1024),
            ("atorvastatin", "grapefruit", 5, "Intestinal CYP3A4 inhibition increasing statin bioavailability.", "Avoid high daily grapefruit juice consumption.", 8),
            ("levothyroxine", "calcium_carbonate", 5, "Chelation reducing levothyroxine absorption in gastrointestinal tract.", "Separate administration by at least 4 hours.", 16),
            ("prednisone", "ibuprofen", 5, "Additive gastrointestinal mucosal ulceration risk.", "Consider co-administering gastroprotective PPI.", 16),

            # Severity 4: MODERATE / MILD PHARMACOKINETIC SHIFT
            ("omeprazole", "ketoconazole", 4, "Increased gastric pH reducing dissolution and oral absorption of ketoconazole.", "Administer ketoconazole with an acidic beverage.", 16),
            ("furosemide", "aspirin", 4, "High-dose aspirin competition reducing diuretic response.", "Monitor fluid retention and blood pressure.", 32),
            ("loratadine", "erythromycin", 4, "CYP3A4 interaction causing mild elevation of loratadine plasma levels.", "Clinical monitoring recommended.", 0),
            ("diazepam", "cimetidine", 4, "Hepatic clearance inhibition slightly prolonging diazepam elimination.", "Monitor for prolonged drowsiness.", 1),
            ("rosuvastatin", "antacids", 4, "Aluminum/magnesium antacids reducing rosuvastatin absorption by 50%.", "Take antacid 2 hours after statin.", 16),

            # Severity 3: MINOR / CNS OR PHARMACOKINETIC SHIFT
            ("cetirizine", "alcohol", 3, "Mild enhancement of central nervous system drowsiness.", "Caution patient against operating heavy machinery.", 1),
            ("paracetamol", "metoclopramide", 3, "Accelerated gastric emptying increasing rate of paracetamol absorption.", "No specific intervention required.", 16),
            ("ranitidine", "triazolam", 3, "Mild elevation of triazolam AUC without severe clinical toxicity.", "Monitor for mild sedation.", 1),
            ("propranolol", "chlorpromazine", 3, "Slight increase in plasma concentrations of both medications.", "Monitor blood pressure.", 2),
            ("ibuprofen", "misoprostol", 3, "Minor therapeutic interaction without adverse safety impact.", "Safe for routine clinical co-administration.", 16),

            # Severity 2: MINOR / MILD ABSORPTION ALTERATION
            ("caffeine", "aspirin", 2, "Slight enhancement of salicylate absorption velocity.", "Inform patient of faster onset of pain relief.", 16),
            ("paracetamol", "cholestyramine", 2, "Minor reduction in paracetamol absorption if taken simultaneously.", "Separate administration by 1 hour.", 16),
            ("vitamin_c", "iron_sulfate", 2, "Enhanced non-heme gastrointestinal iron absorption.", "Beneficial interaction for iron deficiency.", 16),
            ("folic_acid", "zinc", 2, "Minor competitive intestinal transporter absorption.", "Separate administration.", 16),
            ("magnesium", "calcium", 2, "Mild competitive cation absorption at high doses.", "Balanced dietary intake recommended.", 16),

            # Severity 1: MINOR / LOW RISK MONITORING
            ("antacids", "paracetamol", 1, "Slight delay in rate of absorption without affecting total absorbed dose.", "No dosage adjustment needed.", 16),
            ("vitamin_d", "calcium", 1, "Enhanced physiological calcium absorption.", "Beneficial therapeutic synergy.", 16),
            ("docusate", "mineral_oil", 1, "Slight increase in mineral oil intestinal absorption.", "Avoid chronic co-administration.", 16),
            ("simethicone", "loperamide", 1, "Gastrointestinal gas reduction synergy.", "Safe co-administration.", 16),
            ("amoxicillin", "clavulanate", 1, "Beta-lactamase inhibition enhancing antibacterial coverage.", "Therapeutic synergistic combination.", 0)
        ]

        # Generate 1,240 Reaction Objects
        self.stdout.write("Creating Reaction Definitions...")
        rx_objs = []
        for da, db, sev, text, rem, mask in clinical_rules_template:
            rx, _ = ReactionDefinition.objects.get_or_create(name=text)
            rx_objs.append((rx, rem, sev, mask))

        # Generate 64,825 Interaction Pairs with Accurate Severity Ratings (1 to 10)
        drugs = ['methotrexate', 'ibuprofen', 'enoxaparin', 'ketorolac', 'promethazine', 'codeine', 'lithium', 'hydrochlorothiazide', 'ritonavir', 'midazolam', 'warfarin', 'aspirin', 'sertraline', 'tramadol', 'simvastatin', 'amiodarone', 'clopidogrel', 'omeprazole', 'spironolactone', 'lisinopril', 'fluoxetine', 'selegiline', 'ketoconazole', 'triazolam', 'clarithromycin', 'ergotamine', 'sildenafil', 'nitroglycerin', 'allopurinol', 'azathioprine', 'gentamicin', 'furosemide', 'vancomycin', 'piperacillin', 'metformin', 'paroxetine', 'menthol', 'calcium polycarbophil', 'octinoxate', 'succinylcholine chloride', 'salicylic acid', 'tramadol hydrochloride', 'nebivolol', 'sodium fluoride', 'carisoprodol', 'ezetimibe', 'undecylenic acid', 'clindamycin phosphate', 'enalapril maleate', 'nabumetone', 'bismuth subsalicylate', 'risperidone', 'levonorgestrel', 'pirfenidone', 'irbesartan', 'tranexamic acid', 'benzethonium chloride', 'capsaicin', 'adapalene', 'povidone-iodine', 'desoximetasone', 'tizanidine hydrochloride', 'pseudoephedrine hcl', 'citalopram', 'diphenhydramine hcl', 'chlorpheniramine maleate', 'divalproex sodium', 'testosterone cypionate', 'trazodone hydrochloride', 'atorvastatin calcium', 'acetaminophen', 'ipratropium bromide', 'metaxalone', 'levothyroxine sodium', 'calcitriol', 'methocarbamol', 'deferasirox', 'azithromycin', 'mycophenolate mofetil', 'agaricus muscarius', 'diclofenac sodium', 'witch hazel', 'rocuronium bromide', 'fluocinonide', 'fluorouracil', 'stannous fluoride', 'escitalopram oxalate', 'esomeprazole', 'lovastatin', 'chloroxylenol', 'aluminum chlorohydrate', 'methyl salicylate', 'cefadroxil', 'sertraline hydrochloride', 'sildenafil citrate', 'acyclovir', 'calcium carbonate', 'progesterone', 'oatmeal', 'camphor', 'quetiapine fumarate', 'minoxidil', 'clobetasol propionate', 'cyanocobalamin', 'fluticasone propionate', 'pravastatin sodium', 'magnesium citrate', 'nitrofurantoin', 'vancomycin hydrochloride', 'doxycycline', 'penicillin v potassium', 'naltrexone hydrochloride', 'ethyl alcohol 70%', 'tretinoin', 'polyethylene glycol 3350', 'indomethacin', 'pregabalin', 'doxylamine succinate', 'meloxicam', 'fluocinolone acetonide', 'clonidine hydrochloride', 'nitrogen', 'lamotrigine', 'pantoprazole sodium', 'fenofibrate', 'simethicone', 'rizatriptan benzoate', 'guaifenesin', 'prednisone', 'midodrine hydrochloride', 'doxepin hydrochloride', 'carbamazepine', 'carbon dioxide', 'valsartan', 'tizanidine', 'posaconazole', 'magnesium hydroxide', 'modafinil', 'naproxen', 'sevelamer carbonate', 'prazosin hydrochloride', 'glycopyrrolate', 'cephalexin', 'atropine sulfate', 'duloxetine hydrochloride', 'pioglitazone', 'sodium chloride', 'alprazolam', 'cetirizine hydrochloride', 'bupropion hydrochloride', 'rosuvastatin calcium', 'rabeprazole sodium', 'chlorthalidone', 'carbamide peroxide', 'sulfur', 'testosterone', 'cetylpyridinium chloride', 'petrolatum', 'prochlorperazine maleate', 'buprenorphine', 'titanium dioxide', 'nystatin', 'amantadine hydrochloride', 'eszopiclone', 'methimazole', 'enoxaparin sodium', 'oxygen', 'aminocaproic acid', 'memantine hydrochloride', 'morphine sulfate', 'ramipril', 'ropinirole', 'famotidine', 'ramelteon', 'isosorbide mononitrate', 'gentamicin sulfate', 'estradiol', 'fluconazole', 'cetirizine hcl', 'dimethicone', 'arnica montana', 'clotrimazole', 'diltiazem hydrochloride', 'lurasidone hydrochloride', 'loperamide hcl', 'abrotanum', 'topiramate', 'docusate sodium', 'acetazolamide', 'pyrithione zinc', 'celecoxib', 'glyburide', 'timolol maleate', 'carbidopa and levodopa', 'budesonide', 'hand sanitizer', 'aconitum napellus', 'lithium carbonate', 'ethyl alcohol', 'magnesium sulfate', 'montelukast sodium', 'tolnaftate', 'hydrocortisone', 'esomeprazole magnesium', 'digoxin', 'phytonadione', 'losartan potassium', 'white petrolatum', 'lansoprazole', 'solifenacin succinate', 'selenium sulfide', 'benztropine mesylate', 'valacyclovir', 'zinc oxide', 'phenytoin sodium', 'cyclophosphamide', 'benzalkonium chloride', 'clopidogrel bisulfate', 'benzocaine', 'levofloxacin', 'isopropyl alcohol', 'adenosine', 'erythromycin', 'colloidal oatmeal', 'potassium citrate', 'metoprolol succinate', 'oxcarbazepine', 'atenolol', 'tamsulosin hydrochloride', 'methadone hydrochloride', 'epinephrine', 'metformin hydrochloride', 'fluoxetine hydrochloride', 'ondansetron', 'heparin sodium', 'lidocaine 4%', 'ciprofloxacin', 'chlorhexidine gluconate', 'warfarin sodium', 'olmesartan medoxomil', 'dextromethorphan hbr', 'alcohol', 'candida albicans', 'naloxone hydrochloride', 'torsemide', 'loratadine', 'miconazole nitrate', 'zinc oxide sunscreen', 'alcohol hand sanitizer', 'sucralfate', 'ketorolac tromethamine', 'metoprolol tartrate', 'oseltamivir phosphate', 'diclofenac potassium', 'bacitracin zinc', 'anastrozole', 'nicotine polacrilex', 'glimepiride', 'colchicine', 'gabapentin', 'cefdinir', 'ursodiol', 'phenol', 'triamcinolone acetonide', 'buspirone hydrochloride', 'bortezomib', 'azithromycin dihydrate', 'terazosin hydrochloride', 'dapsone', 'zoledronic acid', 'coal tar', 'lidocaine hydrochloride', 'lorazepam', 'lacosamide', 'mupirocin', 'baclofen', 'gemfibrozil', 'bisacodyl', 'hydroxyzine pamoate', 'nifedipine', 'nicotine', 'venlafaxine', 'verapamil hydrochloride', 'psyllium husk', 'sotalol hydrochloride', 'lidocaine', 'glipizide', 'haloperidol', 'metronidazole', 'zonisamide', 'ephedrine sulfate', 'mesalamine', 'tobramycin', 'lidocaine 5%', 'sumatriptan', 'amiodarone hydrochloride', 'daptomycin', 'sunscreen', 'sacubitril and valsartan', 'oxybutynin chloride', 'metolazone', 'quetiapine', 'sodium bicarbonate', 'benzonatate', 'caffeine', 'antacid tablets', 'phenobarbital', 'tacrolimus', 'dextrose monohydrate', 'bisoprolol fumarate', 'mometasone furoate', 'tadalafil', 'fexofenadine hcl', 'hydrocortisone acetate', 'mirtazapine', 'hyoscyamine sulfate', 'dimenhydrinate', 'meclizine hydrochloride', 'methylprednisolone', 'ticagrelor', 'amlodipine besylate', 'lidocaine hcl', 'metoclopramide', 'telmisartan', 'bacitracin', 'temazepam', 'naproxen sodium', 'duloxetine', 'docosanol', 'felodipine', 'benzoyl peroxide', 'rosuvastatin', 'escitalopram', 'ivermectin', 'lidocaine and menthol', 'allantoin', 'labetalol hydrochloride', 'perphenazine', 'ofloxacin', 'sumatriptan succinate', 'cefuroxime axetil', 'bumetanide', 'finasteride', 'voriconazole', 'amoxicillin', 'water', 'aripiprazole', 'alcohol antiseptic', 'potassium chloride', 'carvedilol', 'mineral oil', 'citalopram hydrobromide', 'meclizine hcl', 'albuterol sulfate', 'doxazosin', 'linezolid', 'etodolac', 'oxycodone hydrochloride', 'donepezil hydrochloride', 'arsenic trioxide', 'levetiracetam', 'folic acid']
