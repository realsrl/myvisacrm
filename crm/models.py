from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

class Agencia(models.Model):
    """Representa a una agencia o empresa que gestiona casos de visa."""
    PLAN_CHOICES = [
        ('STARTER', 'Starter'),
        ('GROWTH', 'Growth'),
        ('PRO', 'Pro'),
        ('SCALE', 'Scale'),
        ('ENTERPRISE', 'Enterprise'),
    ]

    nombre = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, help_text="Identificador único en la URL (ej: mi-agencia)")
    logo = models.ImageField(upload_to='agencias/logos/', blank=True, null=True)
    direccion = models.CharField(max_length=255, blank=True)
    telefono = models.CharField(max_length=20, blank=True)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    # Planes y Suscripciones
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default='STARTER')
    stripe_customer_id = models.CharField(max_length=100, blank=True, null=True)
    stripe_subscription_id = models.CharField(max_length=100, blank=True, null=True)
    
    # Límites personalizados (para Enterprise o ajustes manuales)
    limite_casos_custom = models.PositiveIntegerField(null=True, blank=True, help_text="Sobrescribe el límite del plan si se especifica")
    limite_usuarios_custom = models.PositiveIntegerField(null=True, blank=True, help_text="Sobrescribe el límite del plan si se especifica")

    @property
    def limites_actuales(self):
        from .constants import PLAN_DETAILS
        details = PLAN_DETAILS.get(self.plan, PLAN_DETAILS['STARTER'])
        return {
            'casos': self.limite_casos_custom if self.limite_casos_custom is not None else details['casos'],
            'usuarios': self.limite_usuarios_custom if self.limite_usuarios_custom is not None else details['usuarios'],
            'precio_base': details['precio'],
            'usuario_extra': details['usuario_extra']
        }

    @property
    def casos_activos_count(self):
        # Según reglas: Casos = activos (no históricos). Solo casos ARCHIVADOS no cuentan.
        # Casos cerrados siguen contando.
        return self.casos.filter(esta_archivado=False).count()

    @property
    def usuarios_count(self):
        # Según reglas: Usuarios que son CLIENTES no cuentan como usuarios del plan.
        # Solo cuentan los Miembros del Equipo (Preparadores/Staff).
        return self.usuarios.filter(tipo='MIEMBRO').count()
    
    @property
    def uso_casos_porcentaje(self):
        limite = self.limites_actuales['casos']
        if limite == 0: return 0
        return (self.casos_activos_count / limite) * 100

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name_plural = "Agencias"

class UserProfile(models.Model):
    """Extiende el usuario de Django para vincularlo a una agencia."""
    TIPO_CHOICES = [
        ('MIEMBRO', 'Miembro del Equipo'),
        ('CLIENTE', 'Cliente'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    agencia = models.ForeignKey(Agencia, on_delete=models.CASCADE, related_name='usuarios')
    tipo = models.CharField(max_length=15, choices=TIPO_CHOICES, default='MIEMBRO')
    is_demo = models.BooleanField(default=False)
    es_admin_agencia = models.BooleanField(default=False, help_text="Si es True, puede editar configuraciones de la agencia.")

    def __str__(self):
        return f"{self.user.username} - {self.agencia.nombre}"

class CaseStatus(models.Model):
    """Define las etapas del embudo: 'I-130 Pendiente', 'Cita Consular', etc."""
    agencia = models.ForeignKey(Agencia, on_delete=models.CASCADE, related_name='estados_casos', null=True)
    nombre = models.CharField(max_length=100)
    # ... rest remains same but I'll update the whole class for clarity
    orden = models.PositiveIntegerField(default=0, help_text="Define la posición en el embudo")
    color = models.CharField(max_length=7, default="#0d6efd", help_text="Color en formato HEX para las etiquetas")

    class Meta:
        ordering = ['orden']
        verbose_name = "Estado del Caso"
        verbose_name_plural = "Estados de los Casos"

    def __str__(self):
        return f"{self.orden}. {self.nombre} ({self.agencia.nombre if self.agencia else 'Global'})"

class TipoCaso(models.Model):
    agencia = models.ForeignKey(Agencia, on_delete=models.CASCADE, related_name='tipos_casos')
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.nombre} ({self.agencia.nombre})"

class SubTipoCaso(models.Model):
    tipo_caso = models.ForeignKey(TipoCaso, on_delete=models.CASCADE, related_name='subtipos')
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.nombre} - {self.tipo_caso.nombre}"

class Caso(models.Model):
    agencia = models.ForeignKey(Agencia, on_delete=models.CASCADE, related_name='casos', null=True)
    titulo = models.CharField(max_length=200, help_text="Ej: Juan Perez - Residencia")
    tipo = models.ForeignKey(TipoCaso, on_delete=models.SET_NULL, null=True, blank=True)
    sub_tipo = models.ForeignKey(SubTipoCaso, on_delete=models.SET_NULL, null=True, blank=True)
    chat_habilitado = models.BooleanField(
        default=True,
        help_text="Permite al cliente enviar mensajes al preparador desde su portal"
    )
    
    # Relaciones
    beneficiario_principal = models.ForeignKey(User, on_delete=models.CASCADE, related_name='casos_cliente')
    preparador = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='casos_gestionados')
    status_actual = models.ForeignKey(CaseStatus, on_delete=models.PROTECT, related_name='casos')
    
    # Soporte para Casos de Familiares (Sub-casos)
    caso_principal = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='sub_casos')
    derivado = models.ForeignKey('Derivado', on_delete=models.SET_NULL, null=True, blank=True, related_name='caso_especifico')

    # Fechas automáticas
    fecha_apertura = models.DateTimeField(auto_now_add=True)
    ultima_modificacion = models.DateTimeField(auto_now=True)
    
    # Estado de Archivo
    esta_archivado = models.BooleanField(
        default=False, 
        help_text="Los casos archivados no cuentan para el límite del plan, pero no se pueden editar ni reabrir."
    )

    def __str__(self):
        return f"{self.titulo} - {self.status_actual.nombre}"

    def clean(self):
        from django.core.exceptions import ValidationError
        # Solo validar al CREAR un caso nuevo que NO esté marcado como archivado
        if not self.pk and not self.esta_archivado and self.agencia:
            limites = self.agencia.limites_actuales
            if self.agencia.casos_activos_count >= limites['casos']:
                raise ValidationError(
                    f"⚠️ Límite de casos alcanzado ({limites['casos']}) para el plan {self.agencia.plan}. "
                    "Archiva casos antiguos o cambia a un plan superior para continuar."
                )
        
        # Si el caso está archivado, no permitir ciertos cambios si se intenta guardar de nuevo
        if self.pk:
            original = Caso.objects.get(pk=self.pk)
            if original.esta_archivado and not self.esta_archivado:
                raise ValidationError("Un caso archivado no puede ser reabierto.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

class Derivado(models.Model):
    """Familiares incluidos en el mismo caso (hijos, cónyuge)"""
    caso = models.ForeignKey(Caso, on_delete=models.CASCADE, related_name='derivados')
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    telefono = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)

class Actividad(models.Model):
    STATUS_TAREA = [('PENDIENTE', 'Pendiente'), ('EN_PROCESO', 'En Proceso'), ('COMPLETADA', 'Completada')]
    
    caso = models.ForeignKey(Caso, on_delete=models.CASCADE, related_name='actividades')
    titulo = models.CharField(max_length=255)
    detalle = models.TextField(blank=True)
    
    # GESTIÓN DE TIEMPOS 
    fecha_programada = models.DateField(null=True, blank=True, help_text="Cuándo planeas hacerlo")
    fecha_vencimiento = models.DateField(null=True, blank=True, help_text="Fecha límite legal")
    
    status = models.CharField(max_length=15, choices=STATUS_TAREA, default='PENDIENTE')
    prioridad_alta = models.BooleanField(default=False)
    fecha_completada = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['fecha_vencimiento', 'fecha_programada']

    @property
    def semaforo_alerta(self):
        hoy = timezone.now().date()
        if self.status == 'COMPLETADA': return 'success'
        if self.fecha_vencimiento and self.fecha_vencimiento < hoy: return 'danger'
        if self.fecha_programada and self.fecha_programada == hoy: return 'warning'
        return 'info'

from cryptography.fernet import Fernet
from django.conf import settings

class Credencial(models.Model):
    caso = models.ForeignKey(Caso, on_delete=models.CASCADE, related_name='credenciales')
    sitio_web = models.CharField(max_length=100, help_text="Ej: Portal CEAC / USCIS")
    usuario = models.CharField(max_length=150)
    password = models.CharField(max_length=500, help_text="Almacenado de forma cifrada")

    class Meta:
        verbose_name_plural = "Credenciales"

    def save(self, *args, **kwargs):
        # Si el password no parece estar cifrado (Fernet tokens empiezan por gAAAA), lo ciframos
        if self.password and not self.password.startswith('gAAAA'):
            self.set_password(self.password)
        super().save(*args, **kwargs)

    def set_password(self, raw_password):
        f = Fernet(settings.FERNET_KEY)
        self.password = f.encrypt(raw_password.encode()).decode()

    def get_password(self):
        if not self.password: return ""
        try:
            # Si no es un token Fernet, retornamos el valor tal cual (o vacío)
            if not self.password.startswith('gAAAA'): return self.password
            f = Fernet(settings.FERNET_KEY)
            return f.decrypt(self.password.encode()).decode()
        except Exception as e:
            return f"Error de cifrado: {str(e)}"

class CategoriaDocumento(models.Model):
    agencia = models.ForeignKey(Agencia, on_delete=models.CASCADE, related_name='categorias_documentos')
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.nombre} ({self.agencia.nombre})"

    class Meta:
        verbose_name = "Categoría de Documento"
        verbose_name_plural = "Categorías de Documentos"

class Documento(models.Model):
    caso = models.ForeignKey(Caso, on_delete=models.CASCADE, related_name='documentos')
    archivo = models.FileField(upload_to='expedientes/%Y/%m/')
    categoria = models.ForeignKey(CategoriaDocumento, on_delete=models.SET_NULL, related_name='documentos', null=True, blank=True)
    nombre_documento = models.CharField(max_length=255)
    detalle = models.TextField(blank=True, null=True, help_text="Mensaje o detalle del documento")
    # Si True, el cliente puede ver este documento en su portal
    user_can_view = models.BooleanField(
        default=True,
        help_text="Si está activo, el cliente puede ver y descargar este documento desde su portal."
    )
    # Si True, este documento se listará en una sección especial "Llevar a Entrevista" para el cliente
    llevar_a_entrevista = models.BooleanField(
        default=False,
        help_text="Marcar si el cliente debe imprimir y llevar este documento a la entrevista."
    )
    fecha_subida = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nombre_documento} ({self.get_categoria_display()})"

class ActualizacionCliente(models.Model):
    """Lo que el usuario ve en su portal para no llamar por teléfono"""
    caso = models.ForeignKey(Caso, on_delete=models.CASCADE, related_name='actualizaciones')
    mensaje = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha']


class MensajeCliente(models.Model):
    """Mensajes enviados por el cliente al preparador desde el portal"""
    caso = models.ForeignKey(Caso, on_delete=models.CASCADE, related_name='mensajes')
    remitente = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mensajes_enviados')
    contenido = models.TextField(help_text="Escribe tu mensaje al preparador")
    fecha = models.DateTimeField(auto_now_add=True)
    leido = models.BooleanField(default=False)

    class Meta:
        ordering = ['fecha']

    def __str__(self):
        return f"Mensaje de {self.remitente.username} el {self.fecha:%d/%m/%Y %H:%M}"

    @classmethod
    def mensajes_periodo_count(cls, usuario, caso):
        """Cuenta mensajes enviados por el usuario en el período configurado."""
        config = ConfiguracionMensajes.get_config(caso.agencia)
        now = timezone.now()
        if config.periodo == 'DIARIO':
            desde = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif config.periodo == 'SEMANAL':
            desde = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        else:  # MENSUAL
            desde = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return cls.objects.filter(remitente=usuario, caso=caso, fecha__gte=desde).count()


class ConfiguracionMensajes(models.Model):
    """Controla el límite de mensajes que el cliente puede enviar por período, por Agencia."""
    agencia = models.OneToOneField(Agencia, on_delete=models.CASCADE, related_name='config_mensajes', null=True)
    # ...
    PERIODO_CHOICES = [
        ('DIARIO', 'Por Día'),
        ('SEMANAL', 'Por Semana'),
        ('MENSUAL', 'Por Mes'),
    ]
    limite = models.PositiveIntegerField(
        default=5,
        help_text="Número máximo de mensajes permitidos por período"
    )
    periodo = models.CharField(
        max_length=10,
        choices=PERIODO_CHOICES,
        default='DIARIO',
        help_text="Ventana de tiempo en que aplica el límite"
    )

    class Meta:
        verbose_name = "Configuración de Mensajes"
        verbose_name_plural = "Configuración de Mensajes"

    def __str__(self):
        return f"Límite {self.agencia.nombre if self.agencia else 'Global'}: {self.limite} mens/periodo"

    @classmethod
    def get_config(cls, agencia):
        obj, _ = cls.objects.get_or_create(agencia=agencia, defaults={'limite': 5, 'periodo': 'DIARIO'})
        return obj

class ConfiguracionDashboard(models.Model):
    agencia = models.OneToOneField(Agencia, on_delete=models.CASCADE, related_name='config_dashboard', null=True)
    dias_proximos_vencer = models.PositiveIntegerField(default=7, help_text="Días de antelación para mostrar tareas en 'Próximas a Vencer'")

    def __str__(self):
        return f"Config Dashboard - {self.agencia.nombre if self.agencia else 'Global'}"

    class Meta:
        verbose_name = "Configuración del Dashboard"
        verbose_name_plural = "Configuración del Dashboard"

    @classmethod
    def get_config(cls, agencia):
        obj, created = cls.objects.get_or_create(agencia=agencia)
        return obj


class StripeConfig(models.Model):
    """Configuración global de Stripe gestionada desde el admin."""
    public_key = models.CharField(max_length=255, blank=True)
    secret_key = models.CharField(max_length=255, blank=True)
    webhook_secret = models.CharField(max_length=255, blank=True)
    is_live = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Configuración de Stripe"
        verbose_name_plural = "Configuración de Stripe"

    def __str__(self):
        return "Configuración de Stripe " + ("(LIVE)" if self.is_live else "(TEST)")

    @classmethod
    def get_config(cls):
        return cls.objects.first() or cls.objects.create()

class Checklist(models.Model):
    """Plantilla de checklist creada por una agencia."""
    agencia = models.ForeignKey(Agencia, on_delete=models.CASCADE, related_name='checklists')
    nombre = models.CharField(max_length=200)
    creado_el = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nombre} ({self.agencia.nombre})"

    class Meta:
        verbose_name = "Plantilla de Checklist"
        verbose_name_plural = "Plantillas de Checklists"

class ChecklistItem(models.Model):
    """Ítem dentro de una plantilla de checklist."""
    checklist = models.ForeignKey(Checklist, on_delete=models.CASCADE, related_name='items')
    texto = models.CharField(max_length=500)
    orden = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['orden']
        verbose_name = "Ítem de Plantilla"
        verbose_name_plural = "Ítems de Plantilla"

class CaseChecklist(models.Model):
    """Checklist específico asignado a un caso."""
    caso = models.ForeignKey(Caso, on_delete=models.CASCADE, related_name='checklists_asignados')
    checklist_template = models.ForeignKey(Checklist, on_delete=models.SET_NULL, null=True, blank=True)
    nombre = models.CharField(max_length=200)
    fecha_asignado = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nombre} - {self.caso.titulo}"

    class Meta:
        verbose_name = "Checklist Asignado"
        verbose_name_plural = "Checklists Asignados"

class CaseChecklistItem(models.Model):
    """Ítem individual dentro de un checklist asignado a un caso."""
    case_checklist = models.ForeignKey(CaseChecklist, on_delete=models.CASCADE, related_name='items')
    texto = models.CharField(max_length=500)
    completado = models.BooleanField(default=False)
    orden = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['orden']
        verbose_name = "Ítem de Checklist Asignado"
        verbose_name_plural = "Ítems de Checklists Asignados"

