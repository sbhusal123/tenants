# Copyright (c) 2019 Alexander Todorov <atodorov@MrSenko.com>

# Licensed under the GPL 3.0: https://www.gnu.org/licenses/gpl-3.0.txt

from django.conf import settings
from django.http import HttpResponseRedirect
from django.views.generic.base import RedirectView
from django.views.generic.edit import FormView
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import permission_required

from tcms_tenants import utils
from tcms_tenants.forms import NewTenantForm


@method_decorator(permission_required('tcms_tenants.add_tenant'), name='dispatch')
class NewTenantView(FormView):
    """
        Everybody is allowed to create new tenants.
        Depending on additional configuration they may have to pay
        for using them!
    """
    form_class = NewTenantForm

    def get_template_names(self):
        """
            Allow downstream installations to override the template. For example
            to provide a link to SLA or hosting policy! The overriden template
            can extend the base one if needed.
        """
        return ['tcms_tenants/override_new.html', 'tcms_tenants/new.html']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tcms_tenants_domain'] = settings.KIWI_TENANTS_DOMAIN
        return context

    def form_valid(self, form):
        tenant = utils.create_tenant(form.cleaned_data, self.request)
        # all is successfull so redirect to the new tenant
        return HttpResponseRedirect(utils.tenant_url(self.request, tenant.schema_name))


@method_decorator(login_required, name='dispatch')  # pylint: disable=missing-permission-required
class RedirectTo(RedirectView):
    """
        Will redirect to tenant.domain.domain/path!

        Used together with GitHub logins and the ``tenant_url``
        template tag!

        When trying to do GitHub login on a tenant sub-domain
        the HTML href will actually point to

        https://public.tenants.localdomain/login/github?next=/tenants/go/to/tenant/path

        instead of

        http://tenant.tenants.localdomain/login/github?next=path

        This is to prevent redirect_uri mismatch errors!
    """
    def get_redirect_url(self, *args, **kwargs):
        tenant = kwargs['tenant']
        path = kwargs['path']
        return '%s/%s' % (utils.tenant_url(self.request, tenant), path)
