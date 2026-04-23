from django.contrib import admin
from .models import (
    Derivado, Credencial, Agencia, UserProfile, StripeConfig, CaseStatus, Caso, Actividad, Documento,
    ActualizacionCliente, ConfiguracionDashboard, ConfiguracionMensajes,
    Checklist, ChecklistItem, CaseChecklist, CaseChecklistItem
)

@admin.register(Agencia)
class AgenciaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'plan', 'casos_activos_count', 'usuarios_count', 'activo')
    prepopulated_fields = {'slug': ('nombre',)}
    fieldsets = (
        (None, {
            'fields': ('nombre', 'slug', 'logo', 'activo')
        }),
        ('Ubicación y Contacto', {
            'fields': ('direccion', 'telefono')
        }),
        ('Suscripción y Límites', {
            'fields': ('plan', 'stripe_customer_id', 'stripe_subscription_id')
        }),
        ('Límites Personalizados', {
            'fields': ('limite_casos_custom', 'limite_usuarios_custom'),
            'description': 'Solo llenar si se desea sobrescribir los valores por defecto del plan.'
        }),
    )

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'agencia', 'tipo', 'es_admin_agencia')
    list_filter = ('agencia', 'tipo', 'es_admin_agencia')

@admin.register(CaseStatus)
class CaseStatusAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'orden', 'color')
    list_editable = ('orden', 'color')

class DerivadoInline(admin.TabularInline):
    model = Derivado
    extra = 1

class CredencialInline(admin.TabularInline):
    model = Credencial
    extra = 1

@admin.register(Caso)
class CasoAdmin(admin.ModelAdmin):
    list_display = ('id', 'titulo', 'beneficiario_principal', 'preparador', 'status_actual', 'caso_principal', 'esta_archivado', 'fecha_apertura')
    list_editable = ('status_actual', 'esta_archivado')
    list_filter = ('esta_archivado', 'status_actual', 'chat_habilitado', 'tipo', 'sub_tipo', 'preparador', 'caso_principal')
    search_fields = ('titulo', 'beneficiario_principal__username', 'beneficiario_principal__first_name', 'beneficiario_principal__last_name')
    inlines = [DerivadoInline, CredencialInline]
    date_hierarchy = 'fecha_apertura'

@admin.register(Actividad)
class ActividadAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'caso', 'status', 'fecha_vencimiento', 'prioridad_alta')
    list_filter = ('status', 'prioridad_alta', 'fecha_vencimiento')
    search_fields = ('titulo', 'detalle', 'caso__titulo')

@admin.register(Documento)
class DocumentoAdmin(admin.ModelAdmin):
    list_display = ('nombre_documento', 'caso', 'categoria', 'user_can_view', 'fecha_subida')
    list_filter = ('categoria', 'user_can_view', 'fecha_subida')
    search_fields = ('nombre_documento', 'caso__titulo')

admin.site.register(ActualizacionCliente)


@admin.register(ConfiguracionDashboard)
class ConfiguracionDashboardAdmin(admin.ModelAdmin):
    list_display = ('dias_proximos_vencer',)

    def has_add_permission(self, request):
        return not ConfiguracionDashboard.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ConfiguracionMensajes)
class ConfiguracionMensajesAdmin(admin.ModelAdmin):
    """Singleton: no se puede agregar ni eliminar, solo editar el registro único."""
    list_display = ('limite', 'periodo')

    def has_add_permission(self, request):
        # Evitar crear más de uno
        return not ConfiguracionMensajes.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions
@admin.register(StripeConfig)
class StripeConfigAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'is_live')
    
    def has_add_permission(self, request):
        return not StripeConfig.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

class ChecklistItemInline(admin.TabularInline):
    model = ChecklistItem
    extra = 3

@admin.register(Checklist)
class ChecklistAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'agencia', 'creado_el')
    list_filter = ('agencia',)
    search_fields = ('nombre', 'agencia__nombre')
    inlines = [ChecklistItemInline]

class CaseChecklistItemInline(admin.TabularInline):
    model = CaseChecklistItem
    extra = 0

@admin.register(CaseChecklist)
class CaseChecklistAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'caso', 'fecha_asignado')
    list_filter = ('caso__agencia',)
    search_fields = ('nombre', 'caso__titulo')
    inlines = [CaseChecklistItemInline]
