import json

from django.contrib import messages
from django.db.models import ProtectedError
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse


def is_htmx_request(request):
    return request.headers.get("HX-Request") == "true"


class SuccessFeedbackMixin:
    """Aviso de sucesso após salvar/excluir. success_message aceita {object}."""

    success_message = ""

    def get_cancel_url(self):
        # Destino fixo do "Cancelar": funciona mesmo abrindo o formulário direto pelo link
        return str(self.success_url) if self.success_url else reverse("home")

    def get_context_data(self, **kwargs):
        kwargs.setdefault("cancel_url", self.get_cancel_url())
        return super().get_context_data(**kwargs)

    def success_text(self, form):
        # ModelForm: instance já tem os valores novos; DeleteView: form sem instance, usa self.object
        obj = getattr(form, "instance", None) or self.object
        return self.success_message.format(object=obj) if self.success_message else ""

    def form_valid(self, form):
        text = self.success_text(form)  # antes do super(): na exclusão o objeto ainda existe
        response = super().form_valid(form)
        if text:
            messages.success(self.request, text)
        return response

    def htmx_trigger(self, form, done_event):
        # Sem recarregar a página, o aviso vai no cabeçalho; json.dumps escapa acentos (cabeçalho HTTP é ASCII)
        events = {done_event: None}
        text = self.success_text(form)
        if text:
            events["showMessage"] = text
        return json.dumps(events)


class HtmxModalUpdateMixin(SuccessFeedbackMixin):
    modal_form_template_name = None
    modal_success_template_name = None
    modal_object_name = None
    modal_row_id_prefix = None
    modal_done_event = "actionModalDone"  # evento JS que fecha o modal; telas com modal próprio trocam

    def get_template_names(self):
        if is_htmx_request(self.request):
            return [self.modal_form_template_name]
        return super().get_template_names()

    def form_valid(self, form):
        if not is_htmx_request(self.request):
            return super().form_valid(form)

        self.object = form.save()
        response = render(
            self.request,
            self.modal_success_template_name,
            {self.modal_object_name: self.object},
        )
        response["HX-Retarget"] = f"#{self.modal_row_id_prefix}-{self.object.pk}"
        response["HX-Reswap"] = "outerHTML"
        response["HX-Trigger-After-Swap"] = self.htmx_trigger(form, self.modal_done_event)
        return response


class HtmxModalDeleteMixin(SuccessFeedbackMixin):
    modal_confirm_template_name = None
    modal_row_id_prefix = None

    def get_template_names(self):
        if is_htmx_request(self.request):
            return [self.modal_confirm_template_name]
        return super().get_template_names()

    def form_valid(self, form):
        try:
            if not is_htmx_request(self.request):
                return super().form_valid(form)
            pk = self.object.pk
            trigger = self.htmx_trigger(form, "actionModalDone")
            self.object.delete()
        except ProtectedError as e:
            # Registro com dependentes PROTECT (ex.: curso com alunos): avisa em vez de erro 500.
            total = len(e.protected_objects)
            return self.render_to_response(self.get_context_data(
                error=f'Não é possível excluir "{self.object}": existem {total} registro(s) vinculado(s). '
                      "Remova ou transfira esses registros antes."
            ))

        response = HttpResponse()
        response["HX-Retarget"] = f"#{self.modal_row_id_prefix}-{pk}"
        response["HX-Reswap"] = "outerHTML"
        response["HX-Trigger-After-Swap"] = trigger
        return response
