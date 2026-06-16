from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import RespuestaFormulario, Formulario, MensajeInterno
from crm.models import Caso
from django.http import JsonResponse, Http404

from django.core.files.storage import FileSystemStorage
from django.views.decorators.csrf import csrf_exempt
import os

@login_required
def formulario_detalle(request, respuesta_id):
    respuesta_obj = get_object_or_404(RespuestaFormulario, id=respuesta_id)
    formulario = respuesta_obj.formulario
    
    profile = getattr(request.user, 'profile', None)
    is_owner = request.user == respuesta_obj.caso.beneficiario_principal
    is_staff_agency = profile and profile.tipo == 'MIEMBRO' and profile.agencia == respuesta_obj.caso.agencia
    
    if not (is_owner or is_staff_agency):
        messages.error(request, "No tienes permiso para ver este formulario.")
        return redirect('dashboard')

    if request.method == 'POST':
        if respuesta_obj.solo_lectura and not request.user.is_staff:
            messages.error(request, "Este formulario está enviado y no puede ser editado.")
            return redirect('formulario_detalle', respuesta_id=respuesta_id)
        
        datos_actualizados = {}
        fs = FileSystemStorage()

        # Procesar archivos
        for key, file in request.FILES.items():
            if not file:
                continue
            filename = fs.save(f'formularios/respuestas/{key}_{file.name}', file)
            datos_actualizados[key] = fs.url(filename)

        # Procesar campos de texto y otros
        for key, value in request.POST.items():
            if key not in ['csrfmiddlewaretoken', 'action']:
                datos_actualizados[key] = value

        # Preservar datos existentes que no llegaron en el POST
        datos_existentes = dict(respuesta_obj.datos)
        datos_existentes.update(datos_actualizados)
        respuesta_obj.datos = datos_existentes
        
        if request.POST.get('action') == 'send':
            respuesta_obj.estado = 'ENVIADO'
            messages.success(request, "Formulario enviado correctamente.")
        else:
            messages.success(request, "Progreso guardado.")
        
        respuesta_obj.save()
        return redirect('formulario_detalle', respuesta_id=respuesta_id)

    # Obtener secciones a través del modelo intermedio (para el orden personalizado)
    fs_list = formulario.formularioseccion_set.all().order_by('orden').select_related('seccion')
    secciones = [fs.seccion for fs in fs_list]
    
    # Preguntas sueltas (sin sección) vinculadas a este formulario específico
    preguntas_sueltas = formulario.preguntas_sueltas.filter(seccion__isnull=True).order_by('orden')
    
    context = {
        'respuesta': respuesta_obj,
        'formulario': formulario,
        'secciones': secciones,
        'preguntas_sueltas': preguntas_sueltas,
        'readonly': respuesta_obj.solo_lectura and not request.user.is_staff,
        'es_publico': False,
    }
    return render(request, 'formularios/formulario_detalle.html', context)

@login_required
def chat_caso(request, caso_id):
    caso = get_object_or_404(Caso, id=caso_id)
    
    profile = getattr(request.user, 'profile', None)
    is_owner = request.user == caso.beneficiario_principal
    is_staff_agency = profile and profile.tipo == 'MIEMBRO' and profile.agencia == caso.agencia
    
    if not (is_owner or is_staff_agency):
        messages.error(request, "No tienes permiso para acceder a este chat.")
        return redirect('dashboard')
    
    if request.method == 'POST':
        cuerpo = request.POST.get('mensaje')
        adjunto = request.FILES.get('adjunto')
        
        # Identify receptor
        if request.user == caso.beneficiario_principal:
            receptor = caso.preparador
        else:
            receptor = caso.beneficiario_principal
            
        if receptor:
            MensajeInterno.objects.create(
                caso=caso,
                emisor=request.user,
                receptor=receptor,
                cuerpo=cuerpo,
                adjunto=adjunto
            )
            # Logic for email notification could go here
            messages.success(request, "Mensaje enviado.")
        else:
            messages.error(request, "No hay un receptor asignado para este mensaje.")
            
        return redirect('chat_caso', caso_id=caso_id)
        
    mensajes = caso.mensajes_internos.all().order_by('fecha_hora')
    # Mark as read
    mensajes.filter(receptor=request.user, leido=False).update(leido=True)

    return render(request, 'formularios/chat.html', {'caso': caso, 'mensajes': mensajes})


def formulario_publico(request, token):
    """Vista pública para llenar formulario sin autenticación, usando un token único."""
    token_str = str(token)
    respuesta_obj = get_object_or_404(RespuestaFormulario, token=token_str)
    formulario = respuesta_obj.formulario
    caso = respuesta_obj.caso

    es_editable = respuesta_obj.estado == 'BORRADOR'

    if request.method == 'POST':
        if not es_editable:
            messages.error(request, "Este formulario está cerrado y ya no puede ser editado.")
            return redirect('formulario_publico', token=token_str)

        datos_actualizados = {}
        fs = FileSystemStorage()

        for key, file in request.FILES.items():
            # Solo guardar si el usuario realmente seleccionó un archivo
            if file:
                filename = fs.save(f'formularios/publicos/{token_str}_{key}_{file.name}', file)
                datos_actualizados[key] = fs.url(filename)

        for key, value in request.POST.items():
            if key in ['csrfmiddlewaretoken', 'action']:
                continue
            if value or key not in respuesta_obj.datos:
                datos_actualizados[key] = value

        # Preservar datos existentes que no llegaron en el POST
        datos_existentes = dict(respuesta_obj.datos)
        datos_existentes.update(datos_actualizados)
        respuesta_obj.datos = datos_existentes

        if request.POST.get('action') == 'send':
            messages.success(request, "Formulario enviado correctamente.")
        else:
            messages.success(request, "Progreso guardado.")

        respuesta_obj.save()
        return redirect('formulario_publico', token=token_str)

    # Obtener secciones
    fs_list = formulario.formularioseccion_set.all().order_by('orden').select_related('seccion')
    secciones = [fs.seccion for fs in fs_list]
    preguntas_sueltas = formulario.preguntas_sueltas.filter(seccion__isnull=True).order_by('orden')

    context = {
        'respuesta': respuesta_obj,
        'formulario': formulario,
        'secciones': secciones,
        'preguntas_sueltas': preguntas_sueltas,
        'readonly': not es_editable,
        'es_publico': True,
    }
    return render(request, 'formularios/formulario_publico.html', context)
