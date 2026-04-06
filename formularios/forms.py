from django import forms
from .models import Formulario, Seccion, Pregunta, FormularioSeccion

class FormularioForm(forms.ModelForm):
    class Meta:
        model = Formulario
        fields = ['nombre', 'descripcion', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }

class SeccionForm(forms.ModelForm):
    class Meta:
        model = Seccion
        fields = ['nombre', 'descripcion', 'repetible', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'repetible': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }

class PreguntaForm(forms.ModelForm):
    class Meta:
        model = Pregunta
        fields = ['texto_pregunta', 'ayuda_visual', 'tipo_dato', 'orden', 'es_requerida', 'opciones']
        widgets = {
            'texto_pregunta': forms.TextInput(attrs={'class': 'form-control'}),
            'ayuda_visual': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'tipo_dato': forms.Select(attrs={'class': 'form-select'}),
            'orden': forms.NumberInput(attrs={'class': 'form-control'}),
            'es_requerida': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'opciones': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Separar con comas'}),
        }

class FormularioSeccionForm(forms.ModelForm):
    class Meta:
        model = FormularioSeccion
        fields = ['seccion', 'orden']
        widgets = {
            'seccion': forms.Select(attrs={'class': 'form-select'}),
            'orden': forms.NumberInput(attrs={'class': 'form-control'})
        }

    def __init__(self, *args, agencia=None, **kwargs):
        super().__init__(*args, **kwargs)
        if agencia:
            self.fields['seccion'].queryset = Seccion.objects.filter(agencia=agencia)
