# Copyright (c) 2019 Alexander Todorov <atodorov@MrSenko.com>

# Licensed under the GPL 3.0: https://www.gnu.org/licenses/gpl-3.0.txt
# pylint: disable=too-many-ancestors
from datetime import timedelta
from mock import patch

from django.urls import reverse
from django.utils import timezone
from django.conf import settings
from django.contrib.auth.models import Permission
from django.http import HttpResponseRedirect

from tcms_tenants.models import Tenant
from tcms_tenants.tests import LoggedInTestCase


class RedirectToTestCase(LoggedInTestCase):
    def test_redirect_to_tenant_path(self):
        expected_url = 'https://test.%s/plans/search/' % settings.KIWI_TENANTS_DOMAIN
        response = self.client.get(reverse('tcms_tenants:redirect-to',
                                           args=[self.tenant.schema_name, 'plans/search/']))

        self.assertIsInstance(response, HttpResponseRedirect)
        self.assertEqual(response['Location'], expected_url)

    def test_redirect_to_tenant_root_url(self):
        expected_url = 'https://test.%s/' % settings.KIWI_TENANTS_DOMAIN
        response = self.client.get(reverse('tcms_tenants:redirect-to',
                                           args=[self.tenant.schema_name, '']))

        self.assertIsInstance(response, HttpResponseRedirect)
        self.assertEqual(response['Location'], expected_url)


class NewTenantViewTestCase(LoggedInTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        add_tenant = Permission.objects.get(
            content_type__app_label='tcms_tenants',
            codename='add_tenant')
        cls.tester.user_permissions.add(add_tenant)

    def test_create_tenant_shows_defaults_for_trial_and_paid_until(self):
        response = self.client.get(reverse('tcms_tenants:create-tenant'))
        # assert hidden fields are shown with defaults b/c the tests below
        # can't simulate opening the page and clicking the submit button
        self.assertContains(response,
                            '<input id="id_on_trial" name="on_trial" value="True" type="hidden">',
                            html=True)
        self.assertContains(response,
                            '<input id="id_paid_until" name="paid_until" type="hidden">',
                            html=True)

    def test_create_tenant_with_name_schema_only(self):
        expected_url = 'https://tinc.%s' % settings.KIWI_TENANTS_DOMAIN
        response = self.client.post(
            reverse('tcms_tenants:create-tenant'),
            {
                'name': 'Tenant, Inc.',
                'schema_name': 'tinc',
                # this is what the default form view sends
                'on_trial': True,
                'paid_until': '',
            })

        self.assertIsInstance(response, HttpResponseRedirect)
        self.assertEqual(response['Location'], expected_url)

        tenant = Tenant.objects.get(schema_name='tinc')
        self.assertTrue(tenant.on_trial)
        self.assertIsNone(tenant.paid_until)

    def test_create_tenant_with_name_schema_on_trial_payment_date(self):
        """
            Similar invocation will be used via inherited view in
            GitHub Marketplace integration.
        """
        expected_url = 'https://subscriber.%s' % settings.KIWI_TENANTS_DOMAIN
        paid_until = timezone.now().replace(microsecond=0) + timedelta(days=30)

        response = self.client.post(
            reverse('tcms_tenants:create-tenant'),
            {
                'name': 'Subscriber LLC',
                'schema_name': 'subscriber',
                'on_trial': False,
                'paid_until': paid_until.strftime('%Y-%m-%d %H:%M:%S'),
            })

        self.assertIsInstance(response, HttpResponseRedirect)
        self.assertEqual(response['Location'], expected_url)

        tenant = Tenant.objects.get(schema_name='subscriber')
        self.assertFalse(tenant.on_trial)
        self.assertEqual(tenant.paid_until, paid_until)

    @patch('tcms.core.utils.mailto.send_mail')
    def test_creating_tenant_sends_email(self, send_mail):
        response = self.client.post(
            reverse('tcms_tenants:create-tenant'),
            {
                'name': 'Email Ltd',
                'schema_name': 'email',
                'on_trial': True,
                'paid_until': '',
            })

        self.assertIsInstance(response, HttpResponseRedirect)

        self.assertTrue(send_mail.called)
        self.assertEqual(send_mail.call_count, 1)
