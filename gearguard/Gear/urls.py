from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Authentication - Login at root URL
    path('', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    # Dashboard - only at /dashboard/
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Kanban/Requests
    path('kanban/', views.kanban_board, name='kanban'),
    path('request/<int:pk>/start/', views.start_request, name='start_request'),
    path('request/<int:pk>/complete/', views.complete_request, name='complete_request'),
    path('request/<int:pk>/scrap/', views.scrap_request, name='scrap_request'),
    path('update-status/', views.update_status, name='update_status'),
    
    # Calendar
    path('calendar/', views.calendar_view, name='calendar'),
    
    # Equipment
    path('equipment/', views.equipment_list, name='equipment_list'),
    path('equipment/<int:equipment_id>/maintenance/', views.equipment_maintenance, name='equipment_maintenance'),
    
    # Sign Up
    path('signup/', views.signup, name='signup'),
    
    # Password Reset
    path('password_reset/', auth_views.PasswordResetView.as_view(template_name='registration/password_reset_form.html'), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='registration/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'), name='password_reset_complete'),
]
