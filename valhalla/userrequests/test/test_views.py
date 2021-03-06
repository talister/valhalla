from django.test import TestCase
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.utils import timezone
from mixer.backend.django import mixer

from valhalla.accounts.models import Profile
from valhalla.proposals.models import Proposal, Membership
from valhalla.userrequests.models import UserRequest, Request, Molecule
from valhalla.common.test_telescope_states import TelescopeStatesFromFile
from valhalla.common.test_helpers import ConfigDBTestMixin


class TestUserRequestList(TestCase):
    def setUp(self):
        self.user = mixer.blend(User)
        mixer.blend(Profile, user=self.user)
        self.proposals = mixer.cycle(3).blend(Proposal)
        for proposal in self.proposals:
            mixer.blend(Membership, proposal=proposal, user=self.user)
        self.userrequests = mixer.cycle(3).blend(
            UserRequest,
            proposal=(p for p in self.proposals)
        )
        self.requests = mixer.cycle(3).blend(
            Request,
            user_request=(ur for ur in self.userrequests),
        )
        self.client.force_login(self.user)

    def test_userrequest_list(self):
        response = self.client.get(reverse('userrequests:list'))
        for ur in self.userrequests:
            self.assertContains(response, ur.group_id)

    def test_userrequest_no_auth(self):
        self.client.logout()
        response = self.client.get(reverse('userrequests:list'))
        self.assertContains(response, 'Register an Account')

    def test_userrequest_admin(self):
        user = mixer.blend(User, is_staff=True)
        mixer.blend(Profile, user=user)
        self.client.force_login(user)
        response = self.client.get(reverse('userrequests:list'))
        for ur in self.userrequests:
            self.assertNotContains(response, ur.group_id)

    def test_userrequest_admin_staff_view_enabled(self):
        user = mixer.blend(User, is_staff=True)
        mixer.blend(Profile, user=user, staff_view=True)
        self.client.force_login(user)
        response = self.client.get(reverse('userrequests:list'))
        for ur in self.userrequests:
            self.assertContains(response, ur.group_id)

    def test_userrequest_list_only_authored(self):
        self.user.profile.view_authored_requests_only = True
        self.user.profile.save()
        self.userrequests[0].submitter = self.user
        self.userrequests[0].save()
        response = self.client.get(reverse('userrequests:list'))
        self.assertContains(response, self.userrequests[0].group_id)
        self.assertNotContains(response, self.userrequests[1].group_id)

    def test_no_other_requests(self):
        proposal = mixer.blend(Proposal)
        other_ur = mixer.blend(UserRequest, proposal=proposal, group_id=mixer.RANDOM)
        response = self.client.get(reverse('userrequests:list'))
        self.assertNotContains(response, other_ur.group_id)

    def test_filtering(self):
        response = self.client.get(
            reverse('userrequests:list') + '?title={}'.format(self.userrequests[0].group_id)
        )
        self.assertContains(response, self.userrequests[0].group_id)
        self.assertNotContains(response, self.userrequests[1].group_id)
        self.assertNotContains(response, self.userrequests[2].group_id)


class TestUserrequestDetail(TestCase):
    def setUp(self):
        self.user = mixer.blend(User)
        mixer.blend(Profile, user=self.user)
        self.proposal = mixer.blend(Proposal)
        mixer.blend(Membership, proposal=self.proposal, user=self.user)
        self.userrequest = mixer.blend(UserRequest, proposal=self.proposal, group_id=mixer.RANDOM)
        self.requests = mixer.cycle(10).blend(Request, user_request=self.userrequest)
        for request in self.requests:
            mixer.blend(Molecule, request=request, instrument_name='1M0-SCICAM-SBIG')
        self.client.force_login(self.user)

    def test_userrequest_detail(self):
        response = self.client.get(reverse('userrequests:detail', kwargs={'pk': self.userrequest.id}))
        for request in self.requests:
            self.assertContains(response, request.id)

    def test_userrequest_detail_no_auth(self):
        self.client.logout()
        response = self.client.get(reverse('userrequests:detail', kwargs={'pk': self.userrequest.id}))
        self.assertEqual(response.status_code, 404)

    def test_userrequest_detail_admin(self):
        user = mixer.blend(User, is_staff=True)
        mixer.blend(Profile, user=user)
        self.client.force_login(user)
        response = self.client.get(reverse('userrequests:detail', kwargs={'pk': self.userrequest.id}))
        self.assertEqual(response.status_code, 404)

    def test_userrequest_detail_admin_staff_view_enabled(self):
        user = mixer.blend(User, is_staff=True)
        mixer.blend(Profile, user=user, staff_view=True)
        self.client.force_login(user)
        response = self.client.get(reverse('userrequests:detail', kwargs={'pk': self.userrequest.id}))
        for request in self.requests:
            self.assertContains(response, request.id)

    def test_userrequest_detail_only_authored(self):
        self.user.profile.view_authored_requests_only = True
        self.user.profile.save()
        userrequest = mixer.blend(UserRequest, proposal=self.proposal, group_id=mixer.RANDOM, submitter=self.user)
        response = self.client.get(reverse('userrequests:detail', kwargs={'pk': self.userrequest.id}))
        self.assertEqual(response.status_code, 404)
        response = self.client.get(reverse('userrequests:detail', kwargs={'pk': userrequest.id}))
        self.assertContains(response, userrequest.group_id)

    def test_public_userrequest_no_auth(self):
        proposal = mixer.blend(Proposal, public=True)
        self.userrequest.proposal = proposal
        self.userrequest.save()

        self.client.logout()
        response = self.client.get(reverse('userrequests:detail', kwargs={'pk': self.userrequest.id}))
        for request in self.requests:
            self.assertContains(response, request.id)

    def test_single_request_redirect(self):
        userrequest = mixer.blend(UserRequest, proposal=self.proposal, group_id=mixer.RANDOM)
        request = mixer.blend(Request, user_request=userrequest)
        response = self.client.get(reverse('userrequests:detail', kwargs={'pk': userrequest.id}))
        self.assertRedirects(response, reverse('userrequests:request-detail', args=(request.id,)))


class TestRequestDetail(TestCase):
    def setUp(self):
        self.user = mixer.blend(User)
        mixer.blend(Profile, user=self.user)
        self.proposal = mixer.blend(Proposal)
        mixer.blend(Membership, proposal=self.proposal, user=self.user)
        self.userrequest = mixer.blend(UserRequest, proposal=self.proposal, group_id=mixer.RANDOM)
        self.request = mixer.blend(Request, user_request=self.userrequest)
        self.client.force_login(self.user)

    def test_request_detail(self):
        response = self.client.get(reverse('userrequests:request-detail', kwargs={'pk': self.request.id}))
        self.assertContains(response, self.request.id)

    def test_request_detail_no_auth(self):
        self.client.logout()
        response = self.client.get(reverse('userrequests:request-detail', kwargs={'pk': self.request.id}))
        self.assertEqual(response.status_code, 404)

    def test_request_detail_admin(self):
        user = mixer.blend(User, is_staff=True)
        mixer.blend(Profile, user=user)
        self.client.force_login(user)
        response = self.client.get(reverse('userrequests:request-detail', kwargs={'pk': self.request.id}))
        self.assertEqual(response.status_code, 404)

    def test_request_detail_admin_staff_view_enabled(self):
        user = mixer.blend(User, is_staff=True)
        mixer.blend(Profile, user=user, staff_view=True)
        self.client.force_login(user)
        response = self.client.get(reverse('userrequests:request-detail', kwargs={'pk': self.request.id}))
        self.assertContains(response, self.request.id)

    def test_request_detail_only_authored(self):
        self.user.profile.view_authored_requests_only = True
        self.user.profile.save()
        userrequest = mixer.blend(UserRequest, proposal=self.proposal, group_id=mixer.RANDOM, submitter=self.user)
        request = mixer.blend(Request, user_request=userrequest)
        response = self.client.get(reverse('userrequests:request-detail', kwargs={'pk': self.request.id}))
        self.assertEqual(response.status_code, 404)
        response = self.client.get(reverse('userrequests:request-detail', kwargs={'pk': request.id}))
        self.assertContains(response, request.id)

    def test_public_request_detail_no_auth(self):
        proposal = mixer.blend(Proposal, public=True)
        self.userrequest.proposal = proposal
        self.userrequest.save()

        self.client.logout()
        response = self.client.get(reverse('userrequests:request-detail', kwargs={'pk': self.request.id}))
        self.assertContains(response, self.request.id)


class TestTelescopeStates(TelescopeStatesFromFile):
    def setUp(self):
        super().setUp()
        self.user = mixer.blend(User)
        self.client.force_login(self.user)

    def test_date_format_1(self):
        response = self.client.get(reverse('api:telescope_states') + '?start=2016-10-1&end=2016-10-10')
        self.assertContains(response, "lsc")

    def test_date_format_2(self):
        response = self.client.get(reverse('api:telescope_availability') +
                                   '?start=2016-10-1T1:23:44&end=2016-10-10T22:22:2')
        self.assertContains(response, "lsc")

    def test_date_format_bad(self):
        response = self.client.get(reverse('api:telescope_states') +
                                   '?start=2016-10-1%201:3323:44&end=10-10T22:22:2')
        self.assertEqual(response.status_code, 400)
        self.assertIn("minute must be in 0..59", str(response.content))

    def test_no_date_specified(self):
        response = self.client.get(reverse('api:telescope_states'))
        self.assertContains(response, str(timezone.now().date()))


class TestInstrumentInformation(ConfigDBTestMixin, TestCase):
    def test_instrument_information(self):
        response = self.client.get(reverse('api:instruments_information'))
        self.assertIn('1M0-SCICAM-SBIG', response.json())
