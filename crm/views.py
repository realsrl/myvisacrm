from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
from .models import (
    Caso, CaseStatus, Actividad, Documento, ActualizacionCliente,
    MensajeCliente, ConfiguracionMensajes, ConfiguracionDashboard, Credencial
)
from django.contrib.auth.forms import AuthenticationForm
from .forms import DocumentoClienteForm, MensajeClienteForm, ActualizacionForm, NuevoCasoForm
from formularios.models import Formulario, RespuestaFormulario
from django.core.paginator import Paginator
from .constants import PLAN_DETAILS

# ─────────────────────────────────────────────────────────────────────────────
#  PREPARADOR: DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────
def pricing(request):
    # Security: Clients don't manage agency subscriptions
    if request.user.is_authenticated and request.user.profile.tipo == 'CLIENTE':
        return redirect('client_portal')

    # Convertir a lista para facilitar el rendering
    planes = []
    for plan_key, detail in PLAN_DETAILS.items():
        if plan_key != 'ENTERPRISE': # Enterprise se maneja aparte al final
            detail['key'] = plan_key
            planes.append(detail)
    
    enterprise = PLAN_DETAILS['ENTERPRISE']
    enterprise['key'] = 'ENTERPRISE'

    context = {
        'planes': planes,
        'enterprise': enterprise,
    }
    return render(request, 'crm/pricing.html', context)


# @login_required (Removed to allow landing page reach unauthenticated users)
def dashboard(request):
    if not request.user.is_authenticated:
        if request.method == 'POST':
            form = AuthenticationForm(request, data=request.POST)
            if form.is_valid():
                user = form.get_user()
                login(request, user)
                return redirect('dashboard')
        else:
            form = AuthenticationForm()
        return render(request, 'crm/landing.html', {'form': form})
    # Multi-tenant: obtain agency
    if not hasattr(request.user, 'profile'):
        messages.error(request, "Tu usuario no tiene una agencia asignada. Contacta al soporte.")
        return redirect('logout')
        
    # Security Check: Clients should go to their dedicated portal, not the staff dashboard
    if request.user.profile.tipo == 'CLIENTE':
        return redirect('client_portal')

    agencia = request.user.profile.agencia

    hoy = timezone.now().date()
    # Base de actividades del preparador (filtrado por agencia)
    actividades_base = Actividad.objects.filter(
        caso__agencia=agencia
    ).exclude(status='COMPLETADA').select_related('caso')

    vencidas = actividades_base.filter(fecha_vencimiento__lt=hoy).order_by('fecha_vencimiento')
    tareas_hoy = actividades_base.filter(fecha_programada=hoy).order_by('prioridad_alta', 'fecha_vencimiento')

    # Mensajes no respondidos: casos donde el último mensaje es del cliente
    casos_con_mensajes = Caso.objects.filter(preparador=request.user).prefetch_related('mensajes')
    threads_sin_respuesta = []
    for caso in casos_con_mensajes:
        ultimo = caso.mensajes.last()
        if ultimo and ultimo.remitente == caso.beneficiario_principal:
            threads_sin_respuesta.append({
                'caso': caso,
                'ultimo_mensaje': ultimo,
                'total': caso.mensajes.count(),
            })

    # Handle reply from dashboard
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'dashboard_reply':
            caso_pk = request.POST.get('caso_pk')
            contenido = request.POST.get('contenido', '').strip()
            caso_obj = get_object_or_404(Caso, pk=caso_pk, preparador=request.user)
            if contenido:
                MensajeCliente.objects.create(
                    caso=caso_obj,
                    remitente=request.user,
                    contenido=contenido,
                    leido=True,
                )
                messages.success(request, f'💬 Respuesta enviada en "{caso_obj.titulo}".')
            return redirect('dashboard')

    # Actividades próximas a vencer (por agencia)
    config_dash = ConfiguracionDashboard.get_config(agencia)
    fecha_limite = hoy + timezone.timedelta(days=config_dash.dias_proximos_vencer)
    proximas_vencer = actividades_base.filter(
        fecha_vencimiento__gt=hoy,
        fecha_vencimiento__lte=fecha_limite
    ).exclude(fecha_programada=hoy).order_by('fecha_vencimiento')

    # Documentos recientes de su agencia
    documentos_recientes = Documento.objects.filter(
        caso__agencia=agencia
    ).order_by('-fecha_subida')[:10]

    # Todos los casos de la agencia (No archivados por defecto)
    mostrar_archivados = request.GET.get('ver') == 'archivados'
    casos_preparador_qs = Caso.objects.filter(agencia=agencia, esta_archivado=mostrar_archivados).order_by('-fecha_apertura')
    
    # Filtro de búsqueda
    from django.db.models import Q
    query = request.GET.get('q')
    if query:
        casos_preparador_qs = casos_preparador_qs.filter(
            Q(titulo__icontains=query) |
            Q(sub_tipo__icontains=query) |
            Q(beneficiario_principal__first_name__icontains=query) |
            Q(beneficiario_principal__last_name__icontains=query) |
            Q(beneficiario_principal__username__icontains=query) |
            Q(preparador__first_name__icontains=query) |
            Q(preparador__last_name__icontains=query) |
            Q(preparador__username__icontains=query) |
            Q(derivados__nombre__icontains=query) |
            Q(derivados__apellido__icontains=query)
        ).distinct()
    
    # Paginación (Obligatoria según requerimiento)
    paginator = Paginator(casos_preparador_qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Info de Plan y Límites
    limites = agencia.limites_actuales
    casos_activos = agencia.casos_activos_count
    porcentaje_uso = agencia.uso_casos_porcentaje
    
    plan_warning = None
    if porcentaje_uso >= 100:
        plan_warning = "danger"
    elif porcentaje_uso >= 80:
        plan_warning = "warning"

    # Información de Demo (Reset automático)
    is_demo = request.user.profile.is_demo
    if is_demo:
        from django.core.management import call_command
        # Solo resetear si es un acceso normal GET al dashboard (no tras un POST de creación)
        if request.method == 'GET' and not request.GET.get('success'):
             call_command('setup_demo')
             messages.info(request, "🛡️ Modo Demo Activado: Los datos se han reseteado para tu exploración. Nada de lo que crees aquí es persistente.")

    # Form for creating new cases
    nuevo_caso_form = NuevoCasoForm(agencia=agencia)

    context = {
        'vencidas': vencidas,
        'tareas_hoy': tareas_hoy,
        'proximas_vencer': proximas_vencer,
        'config_dash': config_dash,
        'threads_sin_respuesta': threads_sin_respuesta,
        'documentos_recientes': documentos_recientes,
        'page_obj': page_obj,
        'agencia': agencia,
        'limites': limites,
        'casos_activos': casos_activos,
        'porcentaje_uso': porcentaje_uso,
        'plan_warning': plan_warning,
        'ver_archivados': mostrar_archivados,
        'is_demo': is_demo,
        'nuevo_caso_form': nuevo_caso_form,
    }
    return render(request, 'crm/dashboard.html', context)


@login_required
def crear_caso(request):
    """Create a new case from the dashboard modal."""
    profile = request.user.profile
    if profile.tipo != 'MIEMBRO':
        return redirect('client_portal')

    agencia = profile.agencia

    if request.method != 'POST':
        return redirect('dashboard')

    form = NuevoCasoForm(request.POST, agencia=agencia)
    if not form.is_valid():
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f'{form.fields[field].label if field in form.fields else field}: {error}')
        return redirect('dashboard')

    # Check plan limit
    limites = agencia.limites_actuales
    if agencia.casos_activos_count >= limites['casos']:
        messages.error(request, f'⚠️ Límite de casos alcanzado ({limites["casos"]}) para el plan {agencia.plan}. Archiva casos o cambia de plan.')
        return redirect('dashboard')

    from django.contrib.auth.models import User
    from .models import UserProfile, Credencial

    # Create or get client user
    username_cliente = form.cleaned_data['username_cliente']
    password_cliente = form.cleaned_data['password_cliente']
    nombre_cliente = form.cleaned_data['nombre_cliente']
    email_cliente = form.cleaned_data.get('email_cliente', '')

    if User.objects.filter(username=username_cliente).exists():
        cliente_user = User.objects.get(username=username_cliente)
        # Update password if provided
        cliente_user.set_password(password_cliente)
        cliente_user.save()
    else:
        # Split name into first/last
        name_parts = nombre_cliente.split(' ', 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ''

        cliente_user = User.objects.create_user(
            username=username_cliente,
            password=password_cliente,
            first_name=first_name,
            last_name=last_name,
            email=email_cliente,
            is_staff=False,
        )
        # Create UserProfile as CLIENTE for this agency
        UserProfile.objects.create(
            user=cliente_user,
            agencia=agencia,
            tipo='CLIENTE',
        )

    # Create the case
    caso = Caso(
        agencia=agencia,
        titulo=form.cleaned_data['titulo'],
        tipo=form.cleaned_data['tipo'],
        sub_tipo=form.cleaned_data['sub_tipo'],
        beneficiario_principal=cliente_user,
        preparador=form.cleaned_data['preparador'],
        status_actual=form.cleaned_data['status_inicial'],
    )
    caso.save()

    # Auto-save client portal credentials to the vault
    Credencial.objects.create(
        caso=caso,
        sitio_web='Portal MyVisaCRM',
        usuario=username_cliente,
        password=password_cliente,
    )

    messages.success(request, f'✅ Caso "{caso.titulo}" creado exitosamente y asignado a {caso.preparador.get_full_name() or caso.preparador.username}.')
    # Use ?success=true to avoid the demo reset in dashboard view
    return redirect('/?success=true')


# ─────────────────────────────────────────────────────────────────────────────
#  PREPARADOR: FUNNEL / KANBAN
# ─────────────────────────────────────────────────────────────────────────────
@login_required
def funnel_view(request):
    if request.user.profile.tipo != 'MIEMBRO':
        return redirect('client_portal')

    tipo_filtro = request.GET.get('tipo', '')
    sub_tipo_filtro = request.GET.get('sub_tipo', '')

    agencia = request.user.profile.agencia
    estados = CaseStatus.objects.filter(agencia=agencia).order_by('orden')
    casos_preparador = Caso.objects.filter(agencia=agencia).select_related('status_actual')

    if tipo_filtro:
        casos_preparador = casos_preparador.filter(tipo=tipo_filtro)
    if sub_tipo_filtro:
        casos_preparador = casos_preparador.filter(sub_tipo=sub_tipo_filtro)

    casos_por_estado = {estado: [] for estado in estados}
    for caso in casos_preparador:
        casos_por_estado[caso.status_actual].append(caso)

    context = {
        'estados': estados,
        'casos_por_estado': casos_por_estado,
        'tipo_actual': tipo_filtro,
        'sub_tipo_actual': sub_tipo_filtro,
        'tipos': Caso.TIPO_CHOICES,
        'sub_tipos': Caso.SUB_TIPO_CHOICES,
    }
    return render(request, 'crm/funnel.html', context)


# ─────────────────────────────────────────────────────────────────────────────
#  CLIENTE: PORTAL
# ─────────────────────────────────────────────────────────────────────────────
@login_required
def client_portal(request):
    casos = Caso.objects.filter(beneficiario_principal=request.user).order_by('-fecha_apertura')
    
    # Support multiple cases for the same client: select via GET parameter if provided
    caso_pk = request.GET.get('c')
    if caso_pk:
        caso_actual = get_object_or_404(Caso, pk=caso_pk, beneficiario_principal=request.user)
    else:
        caso_actual = casos.first()

    agencia = caso_actual.agencia if caso_actual else None

    config = ConfiguracionMensajes.get_config(agencia) if agencia else None
    doc_form = DocumentoClienteForm()
    msg_form = MensajeClienteForm()
    mensajes_periodo = 0
    puede_enviar_mensaje = False

    if caso_actual and config:
        mensajes_periodo = MensajeCliente.mensajes_periodo_count(request.user, caso_actual)
        puede_enviar_mensaje = mensajes_periodo < config.limite

    if request.method == 'POST' and caso_actual:
        action = request.POST.get('action')

        if action == 'upload_doc':
            doc_form = DocumentoClienteForm(request.POST, request.FILES)
            if doc_form.is_valid():
                doc = doc_form.save(commit=False)
                doc.caso = caso_actual
                doc.categoria = 'CLIENTE'
                doc.user_can_view = True
                doc.save()
                messages.success(request, '✅ Tu documento fue enviado correctamente al preparador.')
                return redirect('client_portal')
            else:
                messages.error(request, '⚠️ Hubo un error al subir el archivo. Verifica los datos.')

        elif action == 'send_message':
            if not puede_enviar_mensaje:
                periodo_label = config.get_periodo_display().lower()
                messages.error(
                    request,
                    f'⛔ Has alcanzado el límite de {config.limite} mensajes {periodo_label}. '
                    'Intenta más tarde.'
                )
            else:
                msg_form = MensajeClienteForm(request.POST)
                if msg_form.is_valid():
                    msg = msg_form.save(commit=False)
                    msg.caso = caso_actual
                    msg.remitente = request.user
                    msg.save()
                    messages.success(request, '💬 Tu mensaje fue enviado al preparador.')
                    return redirect('client_portal')

    documentos_visibles = []
    if caso_actual:
        documentos_visibles = caso_actual.documentos.filter(user_can_view=True).order_by('-fecha_subida')
        mensajes_del_caso = caso_actual.mensajes.all()
    else:
        mensajes_del_caso = MensajeCliente.objects.none()

    context = {
        'casos': casos,
        'caso_actual': caso_actual,
        'doc_form': doc_form,
        'msg_form': msg_form,
        'documentos_visibles': documentos_visibles,
        'mensajes_del_caso': mensajes_del_caso,
        'mensajes_periodo': mensajes_periodo,
        'limite_mensajes': config.limite,
        'periodo_label': config.get_periodo_display(),
        'puede_enviar_mensaje': puede_enviar_mensaje,
        'respuestas_formularios': caso_actual.respuestas_formularios.all() if caso_actual else [],
    }
    return render(request, 'crm/portal.html', context)


# ─────────────────────────────────────────────────────────────────────────────
#  PREPARADOR: DETALLE DEL CASO
# ─────────────────────────────────────────────────────────────────────────────
@login_required
def case_detail(request, pk):
    profile = request.user.profile
    agencia = profile.agencia
    
    # Security: 
    # 1. Company members see all cases in their agency.
    # 2. Clients should NEVER see the internal case detail view.
    if profile.tipo == 'CLIENTE':
        return redirect(f'/portal/?c={pk}')
    
    caso = get_object_or_404(Caso, pk=pk, agencia=agencia)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'reply_message':
            contenido = request.POST.get('contenido', '').strip()
            if contenido:
                MensajeCliente.objects.create(
                    caso=caso,
                    remitente=request.user,
                    contenido=contenido,
                    leido=True,
                )
                messages.success(request, '💬 Respuesta enviada al cliente.')
            else:
                messages.error(request, 'El mensaje no puede estar vacío.')
            return redirect('case_detail', pk=pk)

        elif action == 'update_status':
            actividad_id = request.POST.get('actividad_id')
            nuevo_status = request.POST.get('nuevo_status')
            VALID_STATUSES = [s[0] for s in Actividad.STATUS_TAREA]
            if actividad_id and nuevo_status in VALID_STATUSES:
                actividad = get_object_or_404(Actividad, pk=actividad_id, caso=caso)
                actividad.status = nuevo_status
                actividad.save()
                messages.success(request, f'✅ Tarea actualizada a "{actividad.get_status_display()}".')
            return redirect('case_detail', pk=pk)

        elif action == 'add_actualizacion':
            mensaje = request.POST.get('mensaje', '').strip()
            if mensaje:
                ActualizacionCliente.objects.create(caso=caso, mensaje=mensaje)
                messages.success(request, '📋 Actualización publicada. El cliente ya puede verla.')
            else:
                messages.error(request, 'La actualización no puede estar vacía.')
            return redirect('case_detail', pk=pk)

        elif action == 'assign_form':
            formulario_id = request.POST.get('formulario_id')
            if formulario_id:
                formulario = get_object_or_404(Formulario, pk=formulario_id)
                # Check if already assigned
                if not RespuestaFormulario.objects.filter(caso=caso, formulario=formulario).exists():
                    RespuestaFormulario.objects.create(caso=caso, formulario=formulario)
                    messages.success(request, f'📝 Formulario "{formulario.nombre}" asignado al cliente.')
                else:
                    messages.warning(request, 'Este formulario ya está asignado a este caso.')
            return redirect('case_detail', pk=pk)
        
        elif action == 'toggle_chat':
            caso.chat_habilitado = not caso.chat_habilitado
            caso.save()
            estado = "HABILITADO" if caso.chat_habilitado else "DESHABILITADO"
            messages.info(request, f'💬 El chat ha sido {estado} para este caso.')
            return redirect('case_detail', pk=pk)

        elif action == 'add_credencial':
            sitio = request.POST.get('cred_sitio', '').strip()
            usuario = request.POST.get('cred_usuario', '').strip()
            password = request.POST.get('cred_password', '').strip()
            if sitio and usuario:
                Credencial.objects.create(
                    caso=caso,
                    sitio_web=sitio,
                    usuario=usuario,
                    password=password,
                )
                messages.success(request, f'🔐 Credencial para "{sitio}" guardada en la bóveda.')
            else:
                messages.error(request, 'Debes indicar al menos el sitio y el usuario.')
            return redirect('case_detail', pk=pk)

        elif action == 'add_documento':
            from .forms import DocumentoClienteForm
            doc_form = DocumentoClienteForm(request.POST, request.FILES)
            if doc_form.is_valid():
                doc = doc_form.save(commit=False)
                doc.caso = caso
                doc.categoria = request.POST.get('categoria', 'PREPARADOR')
                doc.user_can_view = request.POST.get('user_can_view') == 'on'
                doc.save()
                messages.success(request, f'📄 Documento "{doc.nombre_documento}" subido correctamente.')
            else:
                messages.error(request, 'Error al subir el documento. Verifica los campos.')
            return redirect('case_detail', pk=pk)

        elif action == 'add_tarea':
            titulo_tarea = request.POST.get('titulo_tarea', '').strip()
            detalle_tarea = request.POST.get('detalle_tarea', '').strip()
            fecha_programada = request.POST.get('fecha_programada') or None
            fecha_vencimiento = request.POST.get('fecha_vencimiento') or None
            prioridad_alta = request.POST.get('prioridad_alta') == 'on'
            if titulo_tarea:
                Actividad.objects.create(
                    caso=caso,
                    titulo=titulo_tarea,
                    detalle=detalle_tarea,
                    fecha_programada=fecha_programada,
                    fecha_vencimiento=fecha_vencimiento,
                    prioridad_alta=prioridad_alta,
                )
                messages.success(request, f'✅ Tarea "{titulo_tarea}" creada.')
            else:
                messages.error(request, 'El título de la tarea es obligatorio.')
            return redirect('case_detail', pk=pk)

    # Marcar mensajes del cliente como leídos
    caso.mensajes.filter(leido=False, remitente=caso.beneficiario_principal).update(leido=True)

    act_form = ActualizacionForm()

    context = {
        'caso': caso,
        'esta_archivado': caso.esta_archivado,
        'actividades': caso.actividades.all(),
        'documentos': caso.documentos.all().order_by('-fecha_subida'),
        'derivados': caso.derivados.all(),
        'credenciales': caso.credenciales.all(),
        'actualizaciones': caso.actualizaciones.all(),
        'mensajes': caso.mensajes.all(),
        'status_choices': Actividad.STATUS_TAREA,
        'act_form': act_form,
        'formularios_disponibles': Formulario.objects.filter(activo=True),
        'respuestas_formularios': caso.respuestas_formularios.all(),
    }
    return render(request, 'crm/case_detail.html', context)

@login_required
def archive_case(request, pk):
    profile = request.user.profile
    if profile.tipo != 'MIEMBRO':
        return redirect('client_portal')
    
    agencia = request.user.profile.agencia
    caso = get_object_or_404(Caso, pk=pk, agencia=agencia)
    
    if request.method == 'POST':
        if not caso.esta_archivado:
            caso.esta_archivado = True
            caso.save()
            messages.success(request, f"📦 Caso '{caso.titulo}' archivado correctamente. No contará en el límite de su plan.")
        return redirect('dashboard')
    
    return render(request, 'crm/archive_confirm.html', {'caso': caso})


def checkout_session(request, plan_key):
    """Crea una sesión de Stripe Checkout para el plan seleccionado."""
    import stripe
    from .models import StripeConfig
    
    if request.user.is_authenticated and request.user.profile.tipo != 'MIEMBRO':
        return redirect('client_portal')

    agencia = getattr(request.user.profile, 'agencia', None) if hasattr(request.user, 'profile') else None
    config = StripeConfig.get_config()
    
    if not config.secret_key:
        messages.error(request, "Stripe no está configurado en el admin.")
        return redirect('pricing')
        
    stripe.api_key = config.secret_key
    
    from .constants import PLAN_DETAILS
    plan = PLAN_DETAILS.get(plan_key)
    if not plan or plan_key == 'ENTERPRISE':
        return redirect('pricing')

    # En una implementación real, tendríamos IDs de precios de Stripe en constants o DB
    # Para esta demo, usamos el nombre y precio dinámico
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': f"Plan {plan_key} - Visa Power CRM",
                    },
                    'unit_amount': int(plan['precio'] * 100),
                    'recurring': {'interval': 'month'},
                },
                'quantity': 1,
            }],
            mode='subscription',
            success_url=request.build_absolute_uri('/') + '?success=true',
            cancel_url=request.build_absolute_uri('/pricing/') + '?cancel=true',
            customer_email=request.user.email if request.user.is_authenticated else None,
            metadata={
                'agencia_id': agencia.id if agencia else 'NEW_AGENCY', 
                'plan': plan_key,
                'user_id': request.user.id if request.user.is_authenticated else 'GUEST'
            }
        )
        return redirect(session.url, code=303)
    except Exception as e:
        messages.error(request, f"Error al contactar con Stripe: {str(e)}")
        return redirect('pricing')

from django.http import JsonResponse
import logging
logger = logging.getLogger(__name__)

@login_required
def validar_acceso_credencial(request, pk):
    """Valida la clave del Preparador antes de entregar el password desencriptado."""
    if not hasattr(request.user, 'profile'):
        return JsonResponse({'status': 'error', 'message': 'Sin agencia'}, status=403)
        
    agencia = request.user.profile.agencia
    if request.method == 'POST' and request.user.profile.tipo == 'MIEMBRO':
        password_preparador = request.POST.get('password_preparador')
        if request.user.check_password(password_preparador):
            credencial = get_object_or_404(Credencial, pk=pk, caso__agencia=agencia)
            decrypted_pass = credencial.get_password()
            
            # Log de auditoría
            logger.info(f"AUDITORÍA: El usuario {request.user.username} accedió a la credencial {credencial.sitio_web} del caso {credencial.caso.id}")
            
            return JsonResponse({'status': 'ok', 'password': decrypted_pass})
        else:
            return JsonResponse({'status': 'error', 'message': 'Contraseña incorrecta'}, status=403)
    
    return JsonResponse({'status': 'error', 'message': 'Método no permitido'}, status=405)
