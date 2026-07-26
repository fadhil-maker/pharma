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
    },
    {
        "group_a": "digoxin",
        "group_b": "furosemide",
        "severity": 8,
        "reaction": "Loop diuretic-induced hypokalemia sensitizing the myocardium to fatal digoxin toxicity.",
        "remedy": "Monitor serum potassium and digoxin levels closely; co-administer potassium supplements.",
        "custom_factors": {}
    },
    {
        "group_a": "lisinopril",
        "group_b": "potassium chloride",
        "severity": 8,
        "reaction": "ACE inhibitor inhibition of aldosterone excretion leading to life-threatening hyperkalemia.",
        "remedy": "Avoid routine potassium supplementation unless hypokalemia is documented.",
        "custom_factors": {"min_age": 50}
    },
    {
        "group_a": "metoprolol",
        "group_b": "clonidine",
        "severity": 8,
        "reaction": "Exaggerated rebound hypertensive crisis upon clonidine withdrawal due to unopposed alpha-stimulation.",
        "remedy": "Taper clonidine slowly and discontinue beta-blocker several days prior.",
        "custom_factors": {}
    },
    {
        "group_a": "amlodipine",
        "group_b": "simvastatin",
        "severity": 6,
        "reaction": "CYP3A4 competition increasing simvastatin exposure and risk of myopathy.",
        "remedy": "Limit simvastatin dose to maximum 20mg daily when co-administered with amlodipine.",
        "custom_factors": {}
    },
    {
        "group_a": "sucralfate",
        "group_b": "ciprofloxacin",
        "severity": 7,
        "reaction": "Aluminum chelation in stomach preventing fluoroquinolone GI absorption.",
        "remedy": "Administer ciprofloxacin at least 2 hours before or 6 hours after sucralfate.",
        "custom_factors": {}
    },
    {
        "group_a": "@ssri",
        "group_b": "sumatriptan",
        "severity": 7,
        "reaction": "Synergistic serotonergic stimulation causing serotonin syndrome symptoms (tremor, hyperreflexia).",
        "remedy": "Monitor patient for weakness, hyperreflexia, and incoordination.",
        "custom_factors": {}
    },
    {
        "group_a": "haloperidol",
        "group_b": "amiodarone",
        "severity": 9,
        "reaction": "Severe cumulative QTc interval prolongation causing ventricular tachycardia (Torsades de Pointes).",
        "remedy": "Avoid combination. Use alternative non-QTc prolonging antipsychotic.",
        "custom_factors": {}
    },
    {
        "group_a": "valproic acid",
        "group_b": "lamotrigine",
        "severity": 8,
        "reaction": "Inhibition of lamotrigine glucuronidation doubling its half-life and triggering toxic epidermal necrolysis / Stevens-Johnson Syndrome.",
        "remedy": "Reduce initial lamotrigine dose by 50% and titrate slowly.",
        "custom_factors": {}
    },
    {
        "group_a": "metformin",
        "group_b": "ethanol",
        "severity": 8,
        "reaction": "Alcohol potentiates metformin's effect on lactate metabolism, triggering fatal lactic acidosis.",
        "remedy": "Advise patient to avoid excessive acute or chronic alcohol consumption.",
        "custom_factors": {}
    },
    {
        "group_a": "insulin glargine",
        "group_b": "@beta_blocker",
        "severity": 7,
        "reaction": "Beta-blocker masks early warning symptoms of hypoglycemia (tachycardia, tremors), except diaphoresis.",
        "remedy": "Educate patient to recognize sweating as primary sign of low blood sugar.",
        "custom_factors": {}
    },
    {
        "group_a": "glimepiride",
        "group_b": "fluconazole",
        "severity": 8,
        "reaction": "CYP2C9 inhibition blocking sulfonylurea breakdown and triggering severe, prolonged hypoglycemic shock.",
        "remedy": "Monitor blood glucose closely and reduce sulfonylurea dose.",
        "custom_factors": {}
    },
    {
        "group_a": "methotrexate",
        "group_b": "ibuprofen",
        "severity": 9,
        "reaction": "NSAID inhibition of renal prostaglandin clearance causing acute methotrexate toxicity and pancytopenia.",
        "remedy": "Avoid high-dose methotrexate co-administration with NSAIDs.",
        "custom_factors": {}
    },
    {
        "group_a": "cyclosporine",
        "group_b": "diltiazem",
        "severity": 7,
        "reaction": "CYP3A4 inhibition by diltiazem raising cyclosporine trough levels.",
        "remedy": "Monitor cyclosporine levels and reduce dose as clinically indicated.",
        "custom_factors": {}
    },
    {
        "group_a": "montelukast",
        "group_b": "prednisone",
        "severity": 2,
        "reaction": "Synergistic therapeutic anti-inflammatory action with minor additive liver metabolism.",
        "remedy": "Standard asthma maintenance protocol; no special monitoring required.",
        "custom_factors": {}
    },
    {
        "group_a": "diphenhydramine",
        "group_b": "ethanol",
        "severity": 7,
        "reaction": "Potent additive central nervous system depression causing severe psychomotor impairment.",
        "remedy": "Warn patient against consuming alcohol while taking sedating antihistamines.",
        "custom_factors": {}
    },
    {
        "group_a": "warfarin",
        "group_b": "metronidazole",
        "severity": 9,
        "reaction": "Inhibition of S-warfarin CYP2C9 metabolism causing massive INR spike and internal hemorrhage.",
        "remedy": "Reduce warfarin dose by 35-50% and monitor INR within 3 days.",
        "custom_factors": {}
    },
    {
        "group_a": "phenytoin",
        "group_b": "folic acid",
        "severity": 4,
        "reaction": "Folic acid replacement acts as co-factor accelerating phenytoin hepatic clearance, reducing seizure control.",
        "remedy": "Monitor therapeutic phenytoin serum levels when initiating folic acid.",
        "custom_factors": {}
    },
    {
        "group_a": "theophylline",
        "group_b": "erythromycin",
        "severity": 8,
        "reaction": "Macrolide inhibition of hepatic CYP1A2 leading to toxic theophylline levels and tachyarrhythmias.",
        "remedy": "Reduce theophylline dosage by 25-50% during macrolide therapy.",
        "custom_factors": {}
    },
    {
        "group_a": "spironolactone",
        "group_b": "losartan",
        "severity": 8,
        "reaction": "Synergistic inhibition of renal potassium excretion resulting in dangerous hyperkalemia.",
        "remedy": "Monitor serum potassium at baseline and 1 week after initiation.",
        "custom_factors": {"min_age": 55}
    },
    {
        "group_a": "tamoxifen",
        "group_b": "paroxetine",
        "severity": 8,
        "reaction": "Potent CYP2D6 inhibition blocking conversion of tamoxifen to active endoxifen, increasing breast cancer recurrence risk.",
        "remedy": "Avoid paroxetine. Switch antidepressant to citalopram or venlafaxine.",
        "custom_factors": {}
    },
    {
        "group_a": "cisplatin",
        "group_b": "gentamicin",
        "severity": 9,
        "reaction": "Additive nephrotoxicity and irreversible ototoxicity leading to acute renal failure and permanent deafness.",
        "remedy": "Avoid combination if possible; perform serial renal panel and audiometry.",
        "custom_factors": {}
    },
    {
        "group_a": "fluorouracil",
        "group_b": "warfarin",
        "severity": 9,
        "reaction": "Inhibition of CYP2C9 by fluorouracil resulting in massive INR elevation and internal bleeding.",
        "remedy": "Monitor INR frequently and reduce anticoagulant dosage.",
        "custom_factors": {}
    },
    {
        "group_a": "cyclophosphamide",
        "group_b": "allopurinol",
        "severity": 8,
        "reaction": "Enhanced bone marrow suppression and severe leukopenia due to delayed metabolite clearance.",
        "remedy": "Monitor complete blood counts weekly.",
        "custom_factors": {}
    },
    {
        "group_a": "phenobarbital",
        "group_b": "oral contraceptives",
        "severity": 7,
        "reaction": "Potent hepatic CYP induction accelerating contraceptive breakdown and causing unplanned pregnancy.",
        "remedy": "Advise non-hormonal barrier contraception.",
        "custom_factors": {}
    },
    {
        "group_a": "oxcarbazepine",
        "group_b": "hydrochlorothiazide",
        "severity": 8,
        "reaction": "Additive renal hyponatremia leading to severe confusion, seizures, and cerebral edema.",
        "remedy": "Monitor serum sodium levels regularly.",
        "custom_factors": {"min_age": 50}
    },
    {
        "group_a": "antacid",
        "group_b": "ketoconazole",
        "severity": 7,
        "reaction": "Gastric acid neutralization preventing dissolution and absorption of azole antifungal.",
        "remedy": "Administer ketoconazole with an acidic beverage (cola) or 2 hours prior to antacids.",
        "custom_factors": {}
    },
    {
        "group_a": "metoclopramide",
        "group_b": "haloperidol",
        "severity": 9,
        "reaction": "Additive dopamine D2 blockade causing severe extrapyramidal symptoms, dystonia, and tardive dyskinesia.",
        "remedy": "Avoid concurrent use.",
        "custom_factors": {}
    },
    {
        "group_a": "domperidone",
        "group_b": "erythromycin",
        "severity": 9,
        "reaction": "CYP3A4 inhibition increasing domperidone levels and causing fatal QTc prolongation / cardiac arrest.",
        "remedy": "CONTRAINDICATED. Do not combine domperidone with macrolides.",
        "custom_factors": {}
    },
    {
        "group_a": "dabigatran",
        "group_b": "dronedarone",
        "severity": 9,
        "reaction": "P-glycoprotein inhibition doubling dabigatran plasma concentration and major bleeding risk.",
        "remedy": "Avoid concurrent use in patients with renal impairment.",
        "custom_factors": {}
    },
    {
        "group_a": "rivaroxaban",
        "group_b": "ketoconazole",
        "severity": 9,
        "reaction": "Combined CYP3A4 and P-gp inhibition causing 160% increase in rivaroxaban AUC and hemorrhage risk.",
        "remedy": "Avoid concurrent systemic azole antifungal therapy with rivaroxaban.",
        "custom_factors": {}
    },
    {
        "group_a": "ticagrelor",
        "group_b": "clarithromycin",
        "severity": 8,
        "reaction": "Strong CYP3A4 inhibition leading to elevated ticagrelor exposure and bleeding toxicity.",
        "remedy": "Avoid co-administration of potent CYP3A4 inhibitors with ticagrelor.",
        "custom_factors": {}
    },
    {
        "group_a": "clozapine",
        "group_b": "ciprofloxacin",
        "severity": 9,
        "reaction": "Potent CYP1A2 inhibition by ciprofloxacin doubling clozapine levels, precipitating seizures and sedation.",
        "remedy": "Reduce clozapine dose by 50% and monitor plasma concentrations.",
        "custom_factors": {}
    },
    {
        "group_a": "lithium",
        "group_b": "lisinopril",
        "severity": 8,
        "reaction": "ACE inhibitor reduction of GFR causing decreased lithium clearance and lithium neurotoxicity.",
        "remedy": "Monitor serum lithium concentrations weekly when starting ACE inhibitors.",
        "custom_factors": {}
    },
    {
        "group_a": "venlafaxine",
        "group_b": "phenelzine",
        "severity": 10,
        "reaction": "Severe, fatal Serotonin Syndrome and malignant hyperthermia.",
        "remedy": "CONTRAINDICATED. Allow a 14-day washout period between MAOIs and SNRIs.",
        "custom_factors": {}
    },
    {
        "group_a": "bupropion",
        "group_b": "selegiline",
        "severity": 10,
        "reaction": "Additive catecholamine stimulation resulting in severe hypertensive crisis and intracranial hemorrhage.",
        "remedy": "CONTRAINDICATED. Do not combine bupropion with MAO-B inhibitors.",
        "custom_factors": {}
    },
    {
        "group_a": "ritonavir",
        "group_b": "midazolam",
        "severity": 10,
        "reaction": "Extreme CYP3A4 inhibition causing prolonged, severe sedation and life-threatening respiratory depression.",
        "remedy": "CONTRAINDICATED. Avoid oral midazolam in patients taking protease inhibitors.",
        "custom_factors": {}
    },
    {
        "group_a": "rifampin",
        "group_b": "warfarin",
        "severity": 8,
        "reaction": "Profound hepatic CYP2C9 and CYP3A4 induction accelerating warfarin clearance and loss of anticoagulation.",
        "remedy": "Increase warfarin dosage and monitor INR every 2 days during co-therapy.",
        "custom_factors": {}
    },
    {
        "group_a": "vancomycin",
        "group_b": "piperacillin-tazobactam",
        "severity": 8,
        "reaction": "Synergistic nephrotoxicity significantly increasing incidence of acute kidney injury.",
        "remedy": "Monitor serum creatinine daily; consider alternative beta-lactam coverage.",
        "custom_factors": {}
    },
    {
        "group_a": "theophylline",
        "group_b": "fluvoxamine",
        "severity": 9,
        "reaction": "Potent CYP1A2 inhibition causing 3-fold to 5-fold increase in theophylline levels and fatal seizures.",
        "remedy": "Avoid combination. Use non-CYP1A2 inhibiting SSRI.",
        "custom_factors": {}
    },
    {
        "group_a": "hydroxychloroquine",
        "group_b": "azithromycin",
        "severity": 8,
        "reaction": "Additive cardiac QTc prolongation and increased risk of ventricular arrhythmias.",
        "remedy": "Obtain baseline ECG and monitor QTc interval.",
        "custom_factors": {}
    },
    {
        "group_a": "glimepiride",
        "group_b": "trimethoprim-sulfamethoxazole",
        "severity": 9,
        "reaction": "CYP2C9 inhibition and protein displacement causing severe, prolonged hypoglycemic coma.",
        "remedy": "Monitor blood glucose frequently; reduce sulfonylurea dose.",
        "custom_factors": {}
    },
    {
        "group_a": "levothyroxine",
        "group_b": "ferrous sulfate",
        "severity": 5,
        "reaction": "Chelation binding in intestinal lumen reducing thyroid hormone absorption and causing hypothyroidism.",
        "remedy": "Separate oral iron and levothyroxine administration by at least 4 hours.",
        "custom_factors": {}
    },
    {
        "group_a": "bromocriptine",
        "group_b": "pseudoephedrine",
        "severity": 8,
        "reaction": "Additive sympathomimetic and vasoconstrictive stimulation triggering severe hypertension and stroke.",
        "remedy": "Avoid concurrent use of oral decongestants with dopamine agonists.",
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
