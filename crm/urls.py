from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('caso/nuevo/', views.crear_caso, name='crear_caso'),
    path('pricing/', views.pricing, name='pricing'),
    path('funnel/', views.funnel_view, name='funnel'),
    path('portal/', views.client_portal, name='client_portal'),
    path('caso/<int:pk>/', views.case_detail, name='case_detail'),
    path('caso/<int:pk>/archivar/', views.archive_case, name='archive_case'),
    path('credencial/<int:pk>/validar/', views.validar_acceso_credencial, name='validar_credencial'),
    path('checkout/<str:plan_key>/', views.checkout_session, name='checkout_session'),
]
