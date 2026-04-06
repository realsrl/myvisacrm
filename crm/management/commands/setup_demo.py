import os
import shutil
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from crm.models import (
    Agencia, UserProfile, CaseStatus, Caso, Actividad,
    MensajeCliente, Documento, Derivado, Credencial,
    TipoCaso, SubTipoCaso, CategoriaDocumento
)
from formularios.models import Formulario, Seccion, Pregunta, FormularioSeccion
from django.utils import timezone
from django.conf import settings

class Command(BaseCommand):
    help = 'Inicializa las cuentas demo con 5 casos, actividades, mensajes, derivados y credenciales (3 por caso).'

    def handle(self, *args, **kwargs):
        self.stdout.write("Configurando Demo de Alta Fidelidad (v3)...")

        # 1. Crear Agencia Demo
        agencia_demo, _ = Agencia.objects.get_or_create(
            slug='demo-agency',
            defaults={'nombre': 'Demo Agency - Visa Power', 'activo': True, 'plan': 'PRO'}
        )

        # 2. Usuarios Demo
        u_agency, created = User.objects.get_or_create(username='agency')
        if created:
            u_agency.set_password('agency123')
            u_agency.first_name = "Agent"
            u_agency.last_name = "Demo"
            u_agency.is_staff = True
            u_agency.save()
        else:
            u_agency.set_password('agency123')
            u_agency.save()

        p_agency, _ = UserProfile.objects.get_or_create(user=u_agency, defaults={'agencia': agencia_demo, 'tipo': 'MIEMBRO', 'is_demo': True, 'es_admin_agencia': True})
        p_agency.is_demo = True
        p_agency.save()

        u_client, created = User.objects.get_or_create(username='client')
        if created:
            u_client.set_password('pass123')
            u_client.first_name = "Client"
            u_client.last_name = "Tester"
            u_client.save()

        p_client, _ = UserProfile.objects.get_or_create(user=u_client, defaults={'agencia': agencia_demo, 'tipo': 'CLIENTE', 'is_demo': True})
        p_client.is_demo = True
        p_client.save()

        # 3. Limpiar datos viejos de la agencia demo
        Caso.objects.filter(agencia=agencia_demo).delete()
        CaseStatus.objects.filter(agencia=agencia_demo).delete()
        TipoCaso.objects.filter(agencia=agencia_demo).delete()  # SubTipos se borran en cascada
        Formulario.objects.filter(agencia=agencia_demo).delete()  # Secciones/Preguntas se borran en cascada
        Seccion.objects.filter(agencia=agencia_demo).delete()
        CategoriaDocumento.objects.filter(agencia=agencia_demo).delete()

        # 4. Configuración inicial de categorías de documentos
        cat_cliente = CategoriaDocumento.objects.create(agencia=agencia_demo, nombre='Subido por Cliente')
        cat_prep = CategoriaDocumento.objects.create(agencia=agencia_demo, nombre='Subido por Preparador')
        cat_entrevista = CategoriaDocumento.objects.create(agencia=agencia_demo, nombre='Llevar a Entrevista')
        cat_otros = CategoriaDocumento.objects.create(agencia=agencia_demo, nombre='Otros')

        # 5. Estados del embudo
        estados = [
            CaseStatus.objects.create(agencia=agencia_demo, nombre='Evaluación Inicial', orden=1, color='#6c757d'),
            CaseStatus.objects.create(agencia=agencia_demo, nombre='Recolección de Documentos', orden=2, color='#0d6efd'),
            CaseStatus.objects.create(agencia=agencia_demo, nombre='Firma y Pago', orden=3, color='#6610f2'),
            CaseStatus.objects.create(agencia=agencia_demo, nombre='Pendiente Aprobación USCIS', orden=4, color='#ffc107'),
            CaseStatus.objects.create(agencia=agencia_demo, nombre='Aprobado / Entrevista', orden=5, color='#198754'),
        ]

        # 5. Tipos y Sub-tipos de Caso (propios de la agencia demo)
        tipo_inmigrante = TipoCaso.objects.create(agencia=agencia_demo, nombre='Inmigrante')
        sub_consular    = SubTipoCaso.objects.create(tipo_caso=tipo_inmigrante, nombre='Proceso Consular')
        sub_ajuste      = SubTipoCaso.objects.create(tipo_caso=tipo_inmigrante, nombre='Ajuste de Estatus')

        tipo_no_inmigrante = TipoCaso.objects.create(agencia=agencia_demo, nombre='No Inmigrante')
        sub_turista     = SubTipoCaso.objects.create(tipo_caso=tipo_no_inmigrante, nombre='Visa Turista / Negocios')
        sub_trabajo     = SubTipoCaso.objects.create(tipo_caso=tipo_no_inmigrante, nombre='Visa de Trabajo')

        tipo_humanitario = TipoCaso.objects.create(agencia=agencia_demo, nombre='Humanitario')
        sub_refugio     = SubTipoCaso.objects.create(tipo_caso=tipo_humanitario, nombre='Refugio / Asilo')

        # 6. Configuración de los 5 casos demo
        casos_info = [
            ("Petición Residencia Familiar (Esposa)",  tipo_inmigrante,    sub_consular,   estados[3]),
            ("Ajuste de Estatus - Inversionista",      tipo_inmigrante,    sub_ajuste,     estados[1]),
            ("Visa Turista - Negocios",                tipo_no_inmigrante, sub_turista,    estados[2]),
            ("Proceso Consular - Hijos",               tipo_inmigrante,    sub_consular,   estados[4]),
            ("Caso de Prueba: Refugio",                tipo_humanitario,   sub_refugio,    estados[0]),
        ]

        dest_dir = os.path.join(settings.MEDIA_ROOT, 'expedientes', '2026', '04')
        os.makedirs(dest_dir, exist_ok=True)
        source_dir = '/Users/edwinciprian/Documents/visapower/static/crm/demofiles'
        hoy = timezone.now().date()

        for i, (titulo, tipo, sub, status) in enumerate(casos_info, 1):
            caso = Caso.objects.create(
                agencia=agencia_demo,
                titulo=f"DEMO: {titulo}",
                tipo=tipo,
                sub_tipo=sub,
                beneficiario_principal=u_client,
                preparador=u_agency,
                status_actual=status
            )

            # --- ACTIVIDADES ---
            Actividad.objects.create(caso=caso, titulo='Verificar antecedentes', status='COMPLETADA', fecha_vencimiento=hoy)
            Actividad.objects.create(caso=caso, titulo='Subir Formulario I-130 / DS-260', status='PENDIENTE', fecha_vencimiento=hoy + timezone.timedelta(days=i*2), prioridad_alta=True)

            # --- FAMILIARES ---
            if i % 2 == 0:
                Derivado.objects.create(caso=caso, nombre=f"Hijo {i}", apellido="Tester", telefono="809-555-0000")

            # --- CHAT ---
            MensajeCliente.objects.create(caso=caso, remitente=u_client, contenido="Hola, ¿cómo va mi proceso?")

            # --- CREDENCIALES (3 por caso) ---
            Credencial.objects.create(caso=caso, sitio_web="Portal CEAC / NVC", usuario=f"user_ceac_{i}", password=f"pass_ceac_{i}_123")
            Credencial.objects.create(caso=caso, sitio_web="USCIS Case Status", usuario=f"receipt_{i}_9988", password=f"secret_{i}_pass")
            Credencial.objects.create(caso=caso, sitio_web="Servicio de Mensajería", usuario=f"client_vpower_{i}", password=f"pwr_{i}_vstrong")

            # --- DOCUMENTOS ---
            files_to_add = [
                (f'passport_{"1" if i==1 else "1"}.png' if i==1 else f"passport{i if i<=5 else 1}.jpeg", "Pasaporte"),
                (f'acta_nacimiento_{i}.jpg', "Acta de Nacimiento"),
                (f'i-864_{i}.pdf', "Formulario I-864"),
            ]

            for filename, label in files_to_add:
                src_path = os.path.join(source_dir, filename)
                if not os.path.exists(src_path):
                    if os.path.isdir(source_dir):
                        all_files = os.listdir(source_dir)
                        if all_files:
                            src_path = os.path.join(source_dir, all_files[0])

                if os.path.exists(src_path):
                    rel_path = f'expedientes/2026/04/{i}_{filename}'
                    full_dest = os.path.join(settings.MEDIA_ROOT, rel_path)
                    os.makedirs(os.path.dirname(full_dest), exist_ok=True)
                    shutil.copy(src_path, full_dest)
                    Documento.objects.create(
                        caso=caso, 
                        archivo=rel_path, 
                        categoria=cat_cliente, 
                        nombre_documento=f"{label} (Demo)"
                    )

        # ── FORMULARIOS DE EJEMPLO ──────────────────────────────────────
        f_i130 = Formulario.objects.create(
            agencia=agencia_demo,
            nombre='Cuestionario Inicial I-130',
            descripcion='Recolecta información para el Peticionario y Beneficiario.',
            activo=True
        )

        s1 = Seccion.objects.create(agencia=agencia_demo, nombre='Datos del Peticionario')
        FormularioSeccion.objects.create(formulario=f_i130, seccion=s1, orden=1)
        Pregunta.objects.create(formulario=f_i130, seccion=s1, texto_pregunta='Nombre Completo', tipo_dato='TEXTO', orden=1)
        Pregunta.objects.create(formulario=f_i130, seccion=s1, texto_pregunta='Fecha de Nacimiento', tipo_dato='FECHA', orden=2)
        Pregunta.objects.create(formulario=f_i130, seccion=s1, texto_pregunta='Estatus Legal', tipo_dato='SELECT', opciones='Ciudadano, Residente', orden=3)

        s2 = Seccion.objects.create(agencia=agencia_demo, nombre='Datos del Beneficiario (Biometría)')
        FormularioSeccion.objects.create(formulario=f_i130, seccion=s2, orden=2)
        Pregunta.objects.create(formulario=f_i130, seccion=s2, texto_pregunta='Número de Pasaporte', tipo_dato='TEXTO', orden=1)
        Pregunta.objects.create(formulario=f_i130, seccion=s2, texto_pregunta='País de Nacimiento', tipo_dato='PAIS', orden=2)

        s3 = Seccion.objects.create(agencia=agencia_demo, nombre='Historial de Empleo', repetible=True)
        FormularioSeccion.objects.create(formulario=f_i130, seccion=s3, orden=3)
        Pregunta.objects.create(formulario=f_i130, seccion=s3, texto_pregunta='Nombre del Empleador', tipo_dato='TEXTO', orden=1)
        Pregunta.objects.create(formulario=f_i130, seccion=s3, texto_pregunta='Cargo/Ocupación', tipo_dato='TEXTO', orden=2)

        self.stdout.write(self.style.SUCCESS(
            f'✅ Demo actualizada: 5 casos, 3 tipos, 5 sub-tipos, 15 credenciales, 10 actividades, 1 formulario con 3 secciones.'
        ))
