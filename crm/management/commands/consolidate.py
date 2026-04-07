"""
Django management command para consolidar todo el código del proyecto
en archivos .txt organizados por aplicación + proyecto completo.
Formato de salida: appname-feb142026-6pm.txt
"""

import os
from pathlib import Path
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings

# ============================================
# CONFIGURACIÓN - EDITA ESTAS VARIABLES
# ============================================
# Ruta del proyecto Django (None = usar settings.BASE_DIR automáticamente)
PROJECT_ROOT = '/Users/edwinciprian/Documents/visapower'

# Carpeta de salida para los archivos consolidados (relativa al proyecto)
OUTPUT_DIR = "/Users/edwinciprian/Documents/visapower/consolidate_code"
# ============================================

class Command(BaseCommand):
    help = 'Consolida todo el código del proyecto Django en archivos .txt por aplicación + proyecto completo'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Determinar ruta del proyecto
        self.project_root = Path(PROJECT_ROOT) if PROJECT_ROOT else Path(settings.BASE_DIR)
        
        # Crear directorio de salida
        self.output_path = self.project_root / OUTPUT_DIR
        self.output_path.mkdir(exist_ok=True, parents=True)
        
        # Extensiones a incluir
        self.include_extensions = {
            '.py', '.html', '.css', '.js', '.json', 
            '.txt', '.md', '.yaml', '.yml', '.ini',
            '.env', '.gitignore', '.xml', '.csv'
        }
        
        # Patrones a excluir
        self.exclude_patterns = {
            '__pycache__', 'migrations', '.git', 'venv', 
            'env', 'node_modules', '.venv', '.idea',
            '*.pyc', '*.pyo', '*.pyd', '.DS_Store',
            '*.sqlite3', '*.db', '*.log', 'db.sqlite3',
            'media', 'staticfiles', 'collectstatic',
            '*.jpg', '*.jpeg', '*.png', '*.gif', '*.svg',
            '*.pdf', '*.zip', '*.tar', '*.gz', '*.exe',
            '*.mp4', '*.mp3', '*.wav', '*.mov'
        }

    def add_arguments(self, parser):
        parser.add_argument(
            '--project',
            type=str,
            help='Ruta manual del proyecto (anula PROJECT_ROOT)',
        )
        parser.add_argument(
            '--output',
            type=str,
            help='Ruta de salida personalizada (anula OUTPUT_DIR)',
        )
        parser.add_argument(
            '--apps',
            nargs='+',
            help='Apps específicas a consolidar (por defecto: todas)',
        )

    def should_include_file(self, file_path):
        """Verifica si el archivo debe incluirse"""
        if file_path.suffix.lower() not in self.include_extensions:
            return False
        
        for pattern in self.exclude_patterns:
            if pattern.startswith('*.'):
                ext = pattern[1:]
                if file_path.match(f"*{ext}"):
                    return False
            elif pattern in str(file_path):
                return False
        return True

    def should_exclude_dir(self, dir_path):
        """Verifica si el directorio debe excluirse"""
        dir_name = dir_path.name
        return (dir_name in self.exclude_patterns or 
                any(pattern in str(dir_path) for pattern in self.exclude_patterns))

    def get_timestamp_suffix(self):
        """Genera sufijo tipo: feb142026-6pm"""
        now = datetime.now()
        month_abbr = now.strftime('%b').lower()
        day = now.day
        year = now.year
        hour = now.hour % 12 or 12
        period = 'am' if now.hour < 12 else 'pm'
        return f"{month_abbr}{day}{year}-{hour}{period}"

    def get_django_apps(self):
        """Obtiene apps Django del proyecto"""
        apps = []
        for app_config in settings.INSTALLED_APPS:
            # Saltar apps de Django/frameworks
            if app_config.startswith((
                'django.', 'rest_framework', 'debug_toolbar',
                'corsheaders', 'crispy_forms', 'allauth'
            )):
                continue
            
            # Buscar app en filesystem
            app_path = self.project_root / app_config.replace('.', '/')
            if app_path.exists() and app_path.is_dir():
                apps.append({
                    'name': app_config,
                    'path': app_path,
                    'short_name': app_config.split('.')[-1]
                })
            else:
                # Buscar en subdirectorios
                for root, dirs, _ in os.walk(self.project_root):
                    potential_name = app_config.split('.')[-1]
                    if potential_name in dirs:
                        app_path = Path(root) / potential_name
                        if (app_path / 'models.py').exists() or (app_path / 'apps.py').exists():
                            apps.append({
                                'name': app_config,
                                'path': app_path,
                                'short_name': potential_name
                            })
                        break
        return apps

    def consolidate_app(self, app_info, timestamp_suffix):
        """Consolida una aplicación específica"""
        app_name = app_info['name']
        app_path = app_info['path']
        short_name = app_info['short_name']
        
        # Nombre del archivo
        output_filename = f"{short_name}-{timestamp_suffix}.txt"
        output_file = self.output_path / output_filename
        
        file_count = 0
        total_size = 0
        
        with open(output_file, 'w', encoding='utf-8') as outfile:
            # Cabecera
            outfile.write("=" * 80 + "\n")
            outfile.write(f"CONSOLIDACIÓN DE CÓDIGO - APLICACIÓN: {app_name}\n")
            outfile.write("=" * 80 + "\n")
            outfile.write(f"Proyecto: {self.project_root.name}\n")
            outfile.write(f"Ruta física: {app_path}\n")
            outfile.write(f"Fecha consolidación: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            outfile.write("=" * 80 + "\n\n")
            
            # Recorrer app
            for root, dirs, files in os.walk(app_path):
                dirs[:] = [d for d in dirs if not self.should_exclude_dir(Path(root) / d)]
                
                for file in sorted(files):
                    file_path = Path(root) / file
                    
                    if self.should_include_file(file_path):
                        rel_path = file_path.relative_to(self.project_root)
                        file_size = file_path.stat().st_size
                        
                        # Escribir info del archivo
                        outfile.write("\n" + "=" * 80 + "\n")
                        outfile.write(f"📁 ARCHIVO: {rel_path}\n")
                        outfile.write(f"📏 Tamaño: {file_size} bytes\n")
                        outfile.write("=" * 80 + "\n\n")
                        
                        try:
                            with open(file_path, 'r', encoding='utf-8') as infile:
                                content = infile.read()
                                outfile.write(content)
                                outfile.write("\n")
                                file_count += 1
                                total_size += file_size
                        except Exception as e:
                            outfile.write(f"❌ ERROR: {e}\n\n")
            
            # Resumen
            outfile.write("\n" + "=" * 80 + "\n")
            outfile.write("📊 RESUMEN DE APLICACIÓN\n")
            outfile.write("=" * 80 + "\n")
            outfile.write(f"Total archivos: {file_count}\n")
            outfile.write(f"Tamaño total: {total_size} bytes ({total_size / 1024:.2f} KB)\n")
            outfile.write("=" * 80 + "\n")
        
        self.stdout.write(
            self.style.SUCCESS(
                f"✓ {short_name:20s} | {file_count:3d} archivos | {total_size / 1024:7.1f} KB → {output_filename}"
            )
        )
        
        return {
            'filename': output_filename,
            'file_count': file_count,
            'total_size': total_size
        }

    def consolidate_project(self, timestamp_suffix, exclude_apps=None):
        """Consolida proyecto completo (excluyendo apps ya procesadas)"""
        if exclude_apps is None:
            exclude_apps = []
        
        output_filename = f"project-{timestamp_suffix}.txt"
        output_file = self.output_path / output_filename
        
        file_count = 0
        total_size = 0
        
        with open(output_file, 'w', encoding='utf-8') as outfile:
            # Cabecera
            outfile.write("=" * 80 + "\n")
            outfile.write(f"CONSOLIDACIÓN COMPLETA - PROYECTO DJANGO\n")
            outfile.write("=" * 80 + "\n")
            outfile.write(f"Proyecto: {self.project_root.name}\n")
            outfile.write(f"Ruta: {self.project_root}\n")
            outfile.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            outfile.write(f"Apps excluidas (consolidadas por separado): {', '.join([a['short_name'] for a in exclude_apps]) or 'Ninguna'}\n")
            outfile.write("=" * 80 + "\n\n")
            
            # Recorrer proyecto
            for root, dirs, files in os.walk(self.project_root):
                dirs[:] = [d for d in dirs if not self.should_exclude_dir(Path(root) / d)]
                
                # Saltar apps ya consolidadas
                skip_dir = any(str(app['path']) in str(root) for app in exclude_apps)
                if skip_dir:
                    continue
                
                for file in sorted(files):
                    file_path = Path(root) / file
                    
                    if self.should_include_file(file_path):
                        rel_path = file_path.relative_to(self.project_root)
                        file_size = file_path.stat().st_size
                        
                        outfile.write("\n" + "=" * 80 + "\n")
                        outfile.write(f"📁 ARCHIVO: {rel_path}\n")
                        outfile.write(f"📏 Tamaño: {file_size} bytes\n")
                        outfile.write("=" * 80 + "\n\n")
                        
                        try:
                            with open(file_path, 'r', encoding='utf-8') as infile:
                                content = infile.read()
                                outfile.write(content)
                                outfile.write("\n")
                                file_count += 1
                                total_size += file_size
                        except Exception as e:
                            outfile.write(f"❌ ERROR: {e}\n\n")
            
            # Resumen
            outfile.write("\n" + "=" * 80 + "\n")
            outfile.write("📊 RESUMEN DEL PROYECTO\n")
            outfile.write("=" * 80 + "\n")
            outfile.write(f"Total archivos: {file_count}\n")
            outfile.write(f"Tamaño total: {total_size} bytes ({total_size / 1024:.2f} KB)\n")
            outfile.write("=" * 80 + "\n")
        
        self.stdout.write(
            self.style.SUCCESS(
                f"✓ proyecto completo    | {file_count:3d} archivos | {total_size / 1024:7.1f} KB → {output_filename}"
            )
        )
        
        return {
            'filename': output_filename,
            'file_count': file_count,
            'total_size': total_size
        }

    def handle(self, *args, **options):
        # Sobreescribir rutas si se pasan como argumentos
        if options['project']:
            self.project_root = Path(options['project'])
            self.stdout.write(self.style.WARNING(f"✓ Ruta proyecto: {self.project_root}"))
        
        if options['output']:
            self.output_path = Path(options['output'])
            self.output_path.mkdir(exist_ok=True, parents=True)
            self.stdout.write(self.style.WARNING(f"✓ Carpeta salida: {self.output_path}"))
        
        # Obtener timestamp
        timestamp_suffix = self.get_timestamp_suffix()
        
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.MIGRATE_HEADING("🚀 CONSOLIDADOR DE CÓDIGO DJANGO"))
        self.stdout.write("=" * 80)
        self.stdout.write(f"📁 Proyecto:   {self.project_root}")
        self.stdout.write(f"📤 Salida:     {self.output_path}")
        self.stdout.write(f"⏱️  Timestamp:  {timestamp_suffix}")
        self.stdout.write("=" * 80 + "\n")
        
        # Obtener apps
        all_apps = self.get_django_apps()
        selected_apps = all_apps
        
        if options['apps']:
            selected_apps = [a for a in all_apps if a['short_name'] in options['apps']]
            self.stdout.write(self.style.WARNING(f"🔍 Filtrando apps: {options['apps']}"))
        
        self.stdout.write(self.style.SUCCESS(f"📦 Encontradas {len(all_apps)} apps Django"))
        if selected_apps:
            self.stdout.write(self.style.SUCCESS(f"🎯 Seleccionadas {len(selected_apps)} apps para consolidar\n"))
        else:
            self.stdout.write(self.style.WARNING("⚠️  No se encontraron apps para consolidar\n"))
            return
        
        # Consolidar apps
        app_results = []
        for app in selected_apps:
            result = self.consolidate_app(app, timestamp_suffix)
            app_results.append(result)
        
        self.stdout.write("")
        
        # Consolidar proyecto completo
        project_result = self.consolidate_project(timestamp_suffix, exclude_apps=selected_apps)
        
        # Resumen final
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("✅ RESUMEN FINAL"))
        self.stdout.write("=" * 80)
        self.stdout.write(f"📁 Carpeta de salida: {self.output_path.absolute()}")
        self.stdout.write(f"📦 Apps consolidadas: {len(app_results)}")
        
        for result in app_results:
            size_kb = result['total_size'] / 1024
            self.stdout.write(f"   • {result['filename']} ({result['file_count']} archivos, {size_kb:.1f} KB)")
        
        proj_size_kb = project_result['total_size'] / 1024
        self.stdout.write(f"   • {project_result['filename']} ({project_result['file_count']} archivos, {proj_size_kb:.1f} KB)")
        
        self.stdout.write("=" * 80)
        self.stdout.write(self.style.SUCCESS("🎉 ¡Consolidación completada exitosamente!"))
        self.stdout.write("=" * 80 + "\n")