"""
URL configuration for app project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.contrib.auth.decorators import login_not_required
from django.urls import include, path

from aluno.views import PublicReportCardView
from curso.views import dashboard

urlpatterns = [
    path('', dashboard, name='home'),
    # Única página pública (fora do LoginRequiredMiddleware): boletim aberto pelo QR Code, com token assinado
    path('boletim/<str:token>/', login_not_required(PublicReportCardView.as_view()), name='report_card_public'),
    path('admin/', admin.site.urls),
    path("cursos/", include("curso.urls")),
    path("alunos/", include("aluno.urls")),
]
