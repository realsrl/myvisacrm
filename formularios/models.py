from django.db import models
from django.contrib.auth.models import User
from crm.models import Caso
from django_countries.fields import CountryField
from localflavor.us.models import USStateField

class Formulario(models.Model):
    nombre = models.CharField(max_length=200, help_text="Ej: Cuestionario Inicial I-130")
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)
    creado_el = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "Molde de Formulario"
        verbose_name_plural = "Moldes de Formularios"

class Seccion(models.Model):
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    repetible = models.BooleanField(default=False, help_text="¿Permitir agregar múltiples instancias (ej: empleos)?")
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name_plural = "Secciones"

class FormularioSeccion(models.Model):
    formulario = models.ForeignKey(Formulario, on_delete=models.CASCADE)
    seccion = models.ForeignKey(Seccion, on_delete=models.CASCADE)
    orden = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['orden']
        unique_together = ('formulario', 'seccion')
        verbose_name_plural = "Secciones"

class Pregunta(models.Model):
    TIPO_DATO_CHOICES = [
        ('TEXTO', 'Texto Corto'),
        ('TEXTAREA', 'Texto Largo'),
        ('FECHA', 'Fecha'),
        ('EMAIL', 'Email'),
        ('NUMERO', 'Número'),
        ('SELECT', 'Selección Múltiple'),
        ('PAIS', 'País'),
        ('ESTADO_US', 'Estado USA'),
        ('DIRECCION_US', 'Dirección USA (Completa)'),
        ('ARCHIVO', 'Archivo / Imagen'),
    ]

    formulario = models.ForeignKey(Formulario, on_delete=models.CASCADE, related_name='preguntas_sueltas', blank=True, null=True)
    seccion = models.ForeignKey(Seccion, on_delete=models.CASCADE, related_name='preguntas', null=True, blank=True)
    texto_pregunta = models.CharField(max_length=500)
    ayuda_visual = models.TextField(blank=True, help_text="Pequeña explicación para el usuario")
    tipo_dato = models.CharField(max_length=20, choices=TIPO_DATO_CHOICES, default='TEXTO')
    orden = models.PositiveIntegerField(default=0)
    es_requerida = models.BooleanField(default=True)
    opciones = models.TextField(blank=True, help_text="Para selección múltiple, separar por comas")

    def save(self, *args, **kwargs):
        # Ya no heredamos del formulario directamente porque la sección es M2M
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.seccion.nombre if self.seccion else 'Pregunta Suelta'} - {self.texto_pregunta}"

    class Meta:
        ordering = ['orden']
        verbose_name = "Pregunta"
        verbose_name_plural = "Preguntas"

class RespuestaFormulario(models.Model):
    ESTADO_CHOICES = [
        ('BORRADOR', 'Borrador'),
        ('ENVIADO', 'Enviado'),
        ('BLOQUEADO', 'Bloqueado'),
    ]

    caso = models.ForeignKey(Caso, on_delete=models.CASCADE, related_name='respuestas_formularios')
    formulario = models.ForeignKey(Formulario, on_delete=models.PROTECT)
    datos = models.JSONField(default=dict, help_text="Almacena todas las respuestas del usuario")
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='BORRADOR')
    ultima_actualizacion = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Respuestas: {self.formulario.nombre} - {self.caso.titulo}"

    @property
    def solo_lectura(self):
        return self.estado in ['ENVIADO', 'BLOQUEADO']

    class Meta:
        verbose_name = "Respuesta de Formulario"
        verbose_name_plural = "Respuestas de Formularios"

class MensajeInterno(models.Model):
    caso = models.ForeignKey(Caso, on_delete=models.CASCADE, related_name='mensajes_internos')
    emisor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mensajes_enviados_internos')
    receptor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mensajes_recibidos_internos')
    cuerpo = models.TextField()
    adjunto = models.FileField(upload_to='mensajeria/%Y/%m/', null=True, blank=True)
    fecha_hora = models.DateTimeField(auto_now_add=True)
    leido = models.BooleanField(default=False)

    def __str__(self):
        return f"Mensaje de {self.emisor} a {self.receptor} - {self.fecha_hora:%d/%m/%Y}"

    class Meta:
        verbose_name = "Mensaje Interno"
        verbose_name_plural = "Mensajes Internos"
        ordering = ['-fecha_hora']
