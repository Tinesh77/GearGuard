from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import date

# Create your models here.

class MaintenanceTeam(models.Model):
    name = models.CharField(max_length=100, unique=True)
    members = models.ManyToManyField(User, blank=True)

    def __str__(self):
        return self.name
    
class Equipment(models.Model):
    CATEGORY_CHOICES = [
        ('Printer', 'Printer'),
        ('Computer', 'Computer'),
        ('Vehicle', 'Vehicle'),
        ('Machinery', 'Machinery'),
        ('HVAC', 'HVAC'),
        ('Power', 'Power'),
        ('Other', 'Other'),
    ]
    
    name = models.CharField(max_length=100)
    serial_number = models.CharField(max_length=100, unique=True)
    department = models.CharField(max_length=100)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='Other')
    assigned_to = models.CharField(
        max_length=100, blank=True, null=True
    )
    purchase_date = models.DateField()
    warranty_expiry = models.DateField(null=True, blank=True)
    location = models.CharField(max_length=100)

    maintenance_team = models.ForeignKey(
        MaintenanceTeam,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    is_scrapped = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} ({self.serial_number})"
    
    def open_requests_count(self):
        return self.maintenancerequest_set.filter(
            status__in=['NEW', 'PRO']
        ).count()

class MaintenanceRequest(models.Model):

    REQUEST_TYPE_CHOICES = [
        ('COR', 'Corrective'),
        ('PRE', 'Preventive'),
    ]

    STATUS_CHOICES = [
        ('NEW', 'New'),
        ('PRO', 'In Progress'),
        ('REP', 'Repaired'),
        ('SCR', 'Scrap'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    # State machine: allowed transitions
    ALLOWED_TRANSITIONS = {
        'NEW': ['PRO', 'SCR'],
        'PRO': ['REP', 'SCR'],
        'REP': [],
        'SCR': [],
    }

    subject = models.CharField(max_length=200)

    equipment = models.ForeignKey(
        Equipment,
        on_delete=models.CASCADE
    )

    request_type = models.CharField(
        max_length=3,
        choices=REQUEST_TYPE_CHOICES
    )
    
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='medium'
    )

    maintenance_team = models.ForeignKey(
        MaintenanceTeam,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    assigned_technician = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    status = models.CharField(
        max_length=3,
        choices=STATUS_CHOICES,
        default='NEW'
    )

    scheduled_date = models.DateField(
        null=True,
        blank=True
    )

    duration_hours = models.FloatField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )
    
    @property
    def is_overdue(self):
        """Returns True if scheduled_date is past and status is NEW or PRO"""
        if self.scheduled_date and self.status in ['NEW', 'PRO']:
            return self.scheduled_date < date.today()
        return False
    
    @property
    def request_id(self):
        """Returns a formatted request ID like REQ-2024-0001"""
        year = self.created_at.year if self.created_at else timezone.now().year
        return f"REQ-{year}-{str(self.pk).zfill(4)}"
    
    def can_transition_to(self, new_status):
        """Check if transition from current status to new_status is allowed"""
        allowed = self.ALLOWED_TRANSITIONS.get(self.status, [])
        return new_status in allowed

    def clean(self):
        # Block creation for scrapped equipment
        if self.pk is None and self.equipment and self.equipment.is_scrapped:
            raise ValidationError(
                "Cannot create maintenance requests for scrapped equipment."
            )
        
        # Duration only allowed if repaired
        if self.duration_hours and self.status != 'REP':
            raise ValidationError(
                "Duration can only be set when status is Repaired."
            )

        # Technician must belong to maintenance team
        if self.assigned_technician and self.maintenance_team:
            if not self.maintenance_team.members.filter(
                id=self.assigned_technician.id
            ).exists():
                raise ValidationError(
                    "Technician must belong to the assigned maintenance team."
                )
                
    def save(self, *args, **kwargs):

        # Auto-fill maintenance team from equipment
        if not self.maintenance_team and self.equipment:
            self.maintenance_team = self.equipment.maintenance_team

        # Apply validation rules
        self.full_clean()

        # Scrap logic
        if self.status == 'SCR':
            self.equipment.is_scrapped = True
            self.equipment.save()

        # Save the instance
        super().save(*args, **kwargs)
        
    def can_user_work(self, user):
        """Check if user is a member of the maintenance team"""
        if not self.maintenance_team:
            return False
        return self.maintenance_team.members.filter(id=user.id).exists()

