from django.core.management.base import BaseCommand
from formularios.models import Formulario, Seccion, Pregunta, FormularioSeccion

class Command(BaseCommand):
    help = 'Seeds the database with I-130 Initial Questionnaire'

    def handle(self, *args, **kwargs):
        f, created = Formulario.objects.get_or_create(
            nombre='Cuestionario Inicial I-130',
            defaults={'descripcion': 'Recolecta información para el Peticionario y Beneficiario.'}
        )

        # 1. Secciones
        s1, _ = Seccion.objects.get_or_create(nombre='Datos del Peticionario')
        FormularioSeccion.objects.get_or_create(formulario=f, seccion=s1, defaults={'orden': 1})
        
        Pregunta.objects.get_or_create(formulario=f, seccion=s1, texto_pregunta='Estatus Legal', tipo_dato='SELECT', opciones='Ciudadano, Residente', orden=3)

        s2, _ = Seccion.objects.get_or_create(nombre='Datos del Beneficiario (Biometría)')
        FormularioSeccion.objects.get_or_create(formulario=f, seccion=s2, defaults={'orden': 2})
        
        Pregunta.objects.get_or_create(formulario=f, seccion=s2, texto_pregunta='Número de Pasaporte', tipo_dato='TEXT', orden=8)
        Pregunta.objects.get_or_create(formulario=f, seccion=s2, texto_pregunta='Foto del Pasaporte', tipo_dato='ARCHIVO', orden=9)

        s3, _ = Seccion.objects.get_or_create(nombre='Historial de Empleo', repetible=True)
        FormularioSeccion.objects.get_or_create(formulario=f, seccion=s3, defaults={'orden': 3})
        
        Pregunta.objects.get_or_create(formulario=f, seccion=s3, texto_pregunta='Nombre del Empleador', tipo_dato='TEXT', orden=1)
        Pregunta.objects.get_or_create(formulario=f, seccion=s3, texto_pregunta='Cargo/Ocupación', tipo_dato='TEXT', orden=2)

        s4, _ = Seccion.objects.get_or_create(nombre='Matrimonios Anteriores', repetible=True)
        FormularioSeccion.objects.get_or_create(formulario=f, seccion=s4, defaults={'orden': 4})
        
        Pregunta.objects.get_or_create(formulario=f, seccion=s4, texto_pregunta='Nombre del Cónyuge Anterior', tipo_dato='TEXT', orden=1)

        # Pregunta Suelta
        Pregunta.objects.get_or_create(formulario=f, seccion=None, texto_pregunta='Notas Finales', tipo_dato='TEXTAREA', orden=99)

        self.stdout.write(self.style.SUCCESS('I-130 Template seeded with M2M sections!'))
