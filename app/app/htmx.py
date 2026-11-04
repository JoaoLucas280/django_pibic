from django.http import HttpResponse
from django.shortcuts import render


def is_htmx_request(request):
    return request.headers.get("HX-Request") == "true"


class HtmxModalUpdateMixin:
    modal_form_template_name = None
    modal_success_template_name = None
    modal_object_name = None
    modal_row_id_prefix = None

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
        response["HX-Trigger-After-Swap"] = "actionModalDone"
        return response


class HtmxModalDeleteMixin:
    modal_confirm_template_name = None
    modal_row_id_prefix = None

    def get_template_names(self):
        if is_htmx_request(self.request):
            return [self.modal_confirm_template_name]
        return super().get_template_names()

    def form_valid(self, form):
        if not is_htmx_request(self.request):
            return super().form_valid(form)

        response = HttpResponse()
        response["HX-Retarget"] = f"#{self.modal_row_id_prefix}-{self.object.pk}"
        response["HX-Reswap"] = "outerHTML"
        response["HX-Trigger-After-Swap"] = "actionModalDone"
        self.object.delete()
        return response
