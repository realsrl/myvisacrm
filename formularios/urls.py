from django.urls import path
from . import views

urlpatterns = [
    path('detalle/<int:respuesta_id>/', views.formulario_detalle, name='formulario_detalle'),
    path('chat/<int:caso_id>/', views.chat_caso, name='chat_caso'),
    path('f/<str:token>/', views.formulario_publico, name='formulario_publico'),
    path('api/auto-save/<int:respuesta_id>/', views.auto_save_formulario, name='auto_save_formulario'),
]
