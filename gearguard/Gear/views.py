from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import MaintenanceRequest, Equipment, MaintenanceTeam
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from datetime import date
import json
from django.db.models import Count
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login as auth_login

def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            return redirect('dashboard')
    else:
        form = UserCreationForm()
    return render(request, 'registration/signup.html', {'form': form})

# Dashboard View
@login_required
def dashboard(request):
    requests = MaintenanceRequest.objects.all()
    
    # Statistics
    total_requests = requests.count()
    new_count = requests.filter(status='NEW').count()
    in_progress_count = requests.filter(status='PRO').count()
    repaired_count = requests.filter(status='REP').count()
    scrap_count = requests.filter(status='SCR').count()
    
    # Calculate overdue count
    overdue_count = sum(1 for r in requests if r.is_overdue)
    
    # Team data for chart
    team_data = MaintenanceTeam.objects.annotate(
        request_count=Count('maintenancerequest')
    )
    team_names = [team.name for team in team_data]
    team_counts = [team.request_count for team in team_data]
    
    # Add unassigned count
    unassigned_count = requests.filter(maintenance_team__isnull=True).count()
    if unassigned_count > 0:
        team_names.append('Unassigned')
        team_counts.append(unassigned_count)
    
    # Equipment list (top 5)
    equipment_list = Equipment.objects.all()[:5]
    
    return render(request, 'dashboard.html', {
        'total_requests': total_requests,
        'new_count': new_count,
        'in_progress_count': in_progress_count,
        'repaired_count': repaired_count,
        'scrap_count': scrap_count,
        'overdue_count': overdue_count,
        'team_names': json.dumps(team_names),
        'team_counts': json.dumps(team_counts),
        'equipment_list': equipment_list,
    })

# Kanban Board View
@login_required
def kanban_board(request):
    statuses = [
        ('NEW', 'New'),
        ('PRO', 'In Progress'),
        ('REP', 'Repaired'),
        ('SCR', 'Scrap'),
    ]

    requests = MaintenanceRequest.objects.select_related('equipment').all()
    
    # Count by status
    status_counts = {
        'NEW': requests.filter(status='NEW').count(),
        'PRO': requests.filter(status='PRO').count(),
        'REP': requests.filter(status='REP').count(),
        'SCR': requests.filter(status='SCR').count(),
    }

    return render(request, 'kanban.html', {
        'statuses': statuses,
        'requests': requests,
        'status_counts': status_counts,
    })

@login_required
def start_request(request, pk):
    req = get_object_or_404(MaintenanceRequest, pk=pk)
    req.assigned_technician = request.user
    req.status = 'PRO'
    req.save()
    return redirect('kanban')

@login_required
def complete_request(request, pk):
    if request.method == 'POST':
        hours = float(request.POST.get('hours'))
        req = get_object_or_404(MaintenanceRequest, pk=pk)
        req.duration_hours = hours
        req.status = 'REP'
        req.save()
    return redirect('kanban')

@login_required
def scrap_request(request, pk):
    req = get_object_or_404(MaintenanceRequest, pk=pk)
    req.status = 'SCR'
    req.save()
    return redirect('kanban')

@require_POST
@login_required
def update_status(request):
    request_id = request.POST.get('id')
    new_status = request.POST.get('status')

    req = get_object_or_404(MaintenanceRequest, id=request_id)

    # Team-based authorization
    if not req.can_user_work(request.user):
        return JsonResponse(
            {'error': 'You are not authorized to work on this request.'},
            status=403
        )
    
    # State machine validation
    if not req.can_transition_to(new_status):
        return JsonResponse(
            {'error': f'Cannot transition from {req.get_status_display()} to {dict(MaintenanceRequest.STATUS_CHOICES).get(new_status, new_status)}.'},
            status=400
        )

    req.status = new_status

    if new_status == 'PRO' and not req.assigned_technician:
        req.assigned_technician = request.user

    req.save()
    return JsonResponse({'success': True})

# Calendar View
@login_required
def calendar_view(request):
    # Get all maintenance requests with scheduled dates
    requests = MaintenanceRequest.objects.filter(
        scheduled_date__isnull=False
    ).select_related('equipment').order_by('scheduled_date')
    
    # Prepare events for calendar
    events = []
    for req in requests:
        events.append({
            'id': req.id,
            'title': f"{req.equipment.name} - {req.subject[:20]}",
            'date': req.scheduled_date.isoformat(),
            'type': req.request_type,
            'status': req.status,
            'equipment': req.equipment.name,
            'subject': req.subject,
        })

    return render(
        request,
        'calendar.html',
        {
            'requests': requests,
            'events': json.dumps(events),
        }
    )

# Equipment List View
@login_required
def equipment_list(request):
    equipment = Equipment.objects.select_related('maintenance_team').all()
    return render(request, 'equipment_list.html', {
        'equipment_list': equipment,
    })

# Equipment Maintenance View
@login_required
def equipment_maintenance(request, equipment_id):
    equipment = get_object_or_404(Equipment, id=equipment_id)
    requests = MaintenanceRequest.objects.filter(equipment=equipment).order_by('-created_at')

    return render(
        request,
        'equipment_maintenance.html',
        {
            'equipment': equipment,
            'requests': requests
        }
    )
