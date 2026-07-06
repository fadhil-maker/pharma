import json
from datetime import datetime, timedelta
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from .models import Drug, ReactionDefinition, Interaction

def get_drugs(request):
    drugs = list(Drug.objects.values('id', 'name', 'activation_time_mins', 'clearance_time_hours'))
    return JsonResponse(drugs, safe=False)

def get_reactions(request):
    reactions = list(ReactionDefinition.objects.values('id', 'name', 'category'))
    return JsonResponse(reactions, safe=False)

@csrf_exempt
def add_reaction(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        reaction, created = ReactionDefinition.objects.get_or_create(
            name=data['name'].strip(),
            defaults={'category': data.get('category', '')}
        )
        return JsonResponse({'status': 'success', 'id': reaction.id, 'name': reaction.name})

@csrf_exempt
def add_interaction(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        interaction, created = Interaction.objects.get_or_create(
            drug_a_id=data['drug_a_id'],
            drug_b_id=data['drug_b_id'],
            reaction_id=data['reaction_id'],
            defaults={'severity_slider': data['severity_slider']}
        )
        return JsonResponse({'status': 'success'})

@csrf_exempt
def check_timeline(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        intakes = data.get('intakes', [])
        
        windows = []
        for item in intakes:
            try:
                drug = Drug.objects.get(id=item['drug_id'])
                intake_time = datetime.fromisoformat(item['timestamp'].replace('Z', '+00:00'))
                
                start_active = intake_time + timedelta(minutes=drug.activation_time_mins)
                end_active = start_active + timedelta(hours=drug.clearance_time_hours)
                
                windows.append({
                    'drug_id': drug.id,
                    'drug_name': drug.name,
                    'start': start_active,
                    'end': end_active
                })
            except Drug.DoesNotExist:
                continue

        warnings = []
        for i in range(len(windows)):
            for j in range(i + 1, len(windows)):
                w1, w2 = windows[i], windows[j]
                
                overlap_start = max(w1['start'], w2['start'])
                overlap_end = min(w1['end'], w2['end'])
                
                if overlap_start < overlap_end:
                    interactions = Interaction.objects.filter(
                        (Q(drug_a_id=w1['drug_id']) & Q(drug_b_id=w2['drug_id'])) |
                        (Q(drug_a_id=w2['drug_id']) & Q(drug_b_id=w1['drug_id']))
                    )
                    
                    for inter in interactions:
                        warnings.append({
                            'drug_a': w1['drug_name'],
                            'drug_b': w2['drug_name'],
                            'reaction': inter.reaction.name,
                            'severity': inter.severity_slider,
                            'overlap_start': overlap_start.isoformat(),
                            'overlap_end': overlap_end.isoformat()
                        })

        return JsonResponse({'warnings': warnings})