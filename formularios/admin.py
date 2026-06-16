from django.contrib import admin
from .models import Formulario, Seccion, FormularioSeccion, Pregunta, RespuestaFormulario, MensajeInterno

class PreguntaInline(admin.TabularInline):
    model = Pregunta
    extra = 1
    sortable_field_name = "orden"

class FormularioSeccionInline(admin.TabularInline):
    model = FormularioSeccion
    extra = 1

class PreguntaSueltaInline(admin.TabularInline):
    model = Pregunta
    extra = 1
    exclude = ('seccion',)
    verbose_name = "Pregunta Suelta (Sin sección)"
    verbose_name_plural = "Preguntas Sueltas"

@admin.register(Formulario)
class FormularioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'agencia', 'activo', 'creado_el')
    list_filter = ('agencia', 'activo')
    inlines = [FormularioSeccionInline, PreguntaSueltaInline]

@admin.register(Seccion)
class SeccionAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'agencia', 'repetible', 'activo')
    list_filter = ('agencia',)
    inlines = [PreguntaInline]

@admin.register(Pregunta)
class PreguntaAdmin(admin.ModelAdmin):
    list_display = ('texto_pregunta', 'seccion', 'formulario', 'tipo_dato', 'orden')
    list_filter = ('tipo_dato', 'formulario', 'seccion')

@admin.register(RespuestaFormulario)
class RespuestaFormularioAdmin(admin.ModelAdmin):
    list_display = ('caso', 'formulario', 'estado', 'cerrado', 'ultima_actualizacion', 'token_corto')
    list_filter = ('estado', 'cerrado', 'formulario')
    readonly_fields = ('ultima_actualizacion', 'token')
    search_fields = ('token', 'caso__titulo', 'formulario__nombre')

    def token_corto(self, obj):
        return obj.token[:16] + '…' if obj.token else '—'
    token_corto.short_description = 'Token'

@admin.register(MensajeInterno)
class MensajeInternoAdmin(admin.ModelAdmin):
    list_display = ('emisor', 'receptor', 'caso', 'fecha_hora', 'leido')
    list_filter = ('leido', 'fecha_hora')
