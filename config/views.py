from django.views.generic import TemplateView


class IndexView(TemplateView):
    template_name = 'index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            from apps.usuarios.models import Usuario
            from apps.cursos.models import Curso
            from apps.inscripciones.models import Inscripcion
            context['total_cursos'] = Curso.objects.filter(estado='publicado').count()
            context['total_estudiantes'] = Usuario.objects.filter(rol='estudiante').count()
            context['total_profesores'] = Usuario.objects.filter(rol='profesor').count()
            context['total_inscripciones'] = Inscripcion.objects.filter(estado='activa').count()
        except Exception:
            context['total_cursos'] = 0
            context['total_estudiantes'] = 0
            context['total_profesores'] = 0
            context['total_inscripciones'] = 0
        return context
