from valhalla.userrequests.models import UserRequest, Request, DraftUserRequest, Window, Molecule, Target, Constraints, Location
from valhalla.proposals.models import Proposal, Membership, TimeAllocation, Semester
from valhalla.common.test_helpers import ConfigDBTestMixin, SetTimeMixin
import valhalla.userrequests.signals.handlers  # noqa
from valhalla.userrequests.test.test_state_changes import PondMolecule, PondBlock

from django.core.urlresolvers import reverse
from django.core.serializers.json import DjangoJSONEncoder
from django.contrib.auth.models import User
from django.conf import settings
from rest_framework.test import APITestCase
from mixer.backend.django import mixer
from mixer.main import mixer as basic_mixer
from unittest.mock import patch
from django.utils import timezone
from datetime import datetime, timedelta
import responses
import os
import copy
import json

generic_payload = {
    'proposal': 'temp',
    'group_id': 'test group',
    'operator': 'SINGLE',
    'ipp_value': 1.0,
    'observation_type': 'NORMAL',
    'requests': [{
        'target': {
            'name': 'fake target',
            'type': 'SIDEREAL',
            'dec': 20,
            'ra': 34.4,
        },
        'molecules': [{
            'type': 'EXPOSE',
            'instrument_name': '1M0-SCICAM-SBIG',
            'filter': 'air',
            'exposure_time': 100,
            'exposure_count': 1,
            'bin_x': 1,
            'bin_y': 1,
        }],
        'windows': [{
            'start': '2016-09-29T21:12:18Z',
            'end': '2016-10-29T21:12:19Z'
        }],
        'location': {
            'telescope_class': '1m0',
        },
        'constraints': {
            'max_airmass': 2.0,
            'min_lunar_distance': 30.0,
        }
    }]
}


class TestUserGetRequestApi(ConfigDBTestMixin, SetTimeMixin, APITestCase):
    def setUp(self):
        super().setUp()
        self.proposal = mixer.blend(Proposal)
        self.user = mixer.blend(User, is_staff=False, is_superuser=False)
        self.other_user = mixer.blend(User, is_staff=False, is_superuser=False)
        mixer.blend(Membership, user=self.user, proposal=self.proposal)
        self.staff_user = mixer.blend(User, is_staff=True)

    def test_get_user_request_detail_unauthenticated(self):
        self.client.force_login(self.other_user)
        user_request = mixer.blend(UserRequest, submitter=self.user, proposal=self.proposal, group_id="testgroup")
        result = self.client.get(reverse('api:user_requests-detail', args=(user_request.id,)))
        self.assertEqual(result.status_code, 404)

    def test_get_user_request_detail_authenticated(self):
        user_request = mixer.blend(UserRequest, submitter=self.user, proposal=self.proposal, group_id="testgroup")
        self.client.force_login(self.user)
        result = self.client.get(reverse('api:user_requests-detail', args=(user_request.id,)))
        self.assertContains(result, user_request.group_id)

    def test_get_user_request_list_unauthenticated(self):
        self.client.force_login(self.other_user)
        mixer.blend(UserRequest, submitter=self.user, proposal=self.proposal, group_id="testgroup")
        result = self.client.get(reverse('api:user_requests-list'))
        self.assertEquals(result.status_code, 200)
        self.assertEquals(result.json()['results'], [])

    def test_get_user_request_list_authenticated(self):
        user_request = mixer.blend(UserRequest, submitter=self.user, proposal=self.proposal, group_id="testgroup")
        self.client.force_login(self.user)
        result = self.client.get(reverse('api:user_requests-list'))
        self.assertContains(result, user_request.group_id)

    def test_get_user_request_list_staff(self):
        user_request = mixer.blend(UserRequest, submitter=self.user, proposal=self.proposal, group_id="testgroup2")
        self.client.force_login(self.staff_user)
        result = self.client.get(reverse('api:user_requests-list'))
        self.assertContains(result, user_request.group_id)

    def test_get_user_request_detail_public(self):
        proposal = mixer.blend(Proposal, public=True)
        user_request = mixer.blend(UserRequest, submitter=self.user, proposal=proposal, group_id="publicgroup")
        result = self.client.get(reverse('api:user_requests-detail', args=(user_request.id,)))
        self.assertContains(result, user_request.group_id)


class TestUserPostRequestApi(ConfigDBTestMixin, SetTimeMixin, APITestCase):
    def setUp(self):
        super().setUp()
        self.proposal = mixer.blend(Proposal)
        self.user = mixer.blend(User)
        self.client.force_login(self.user)
        semester = mixer.blend(Semester, id='2016B', start=datetime(2016, 9, 1, tzinfo=timezone.utc),
                               end=datetime(2016, 12, 31, tzinfo=timezone.utc)
                               )
        self.time_allocation_1m0 = mixer.blend(TimeAllocation, proposal=self.proposal, semester=semester,
                                               telescope_class='1m0', std_allocation=100.0, std_time_used=0.0,
                                               too_allocation=10, too_time_used=0.0, ipp_limit=10.0,
                                               ipp_time_available=5.0)

        mixer.blend(Membership, user=self.user, proposal=self.proposal)
        self.generic_payload = copy.deepcopy(generic_payload)
        self.generic_payload['proposal'] = self.proposal.id

    def test_post_userrequest_unauthenticated(self):
        self.other_user = mixer.blend(User)
        self.client.force_login(self.other_user)
        response = self.client.post(reverse('api:user_requests-list'), data=self.generic_payload)
        self.assertEqual(response.status_code, 400)

    def test_post_userrequest_authenticated(self):
        response = self.client.post(reverse('api:user_requests-list'), data=self.generic_payload)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['group_id'], self.generic_payload['group_id'])

    def test_post_userrequest_wrong_proposal(self):
        bad_data = self.generic_payload.copy()
        bad_data['proposal'] = 'DoesNotExist'
        response = self.client.post(reverse('api:user_requests-list'), data=bad_data)
        self.assertEqual(response.status_code, 400)

    def test_post_userrequest_no_membership(self):
        proposal = mixer.blend(Proposal)
        bad_data = self.generic_payload.copy()
        bad_data['proposal'] = proposal.id
        response = self.client.post(reverse('api:user_requests-list'), data=bad_data)
        self.assertIn('You do not belong', str(response.content))
        self.assertEqual(response.status_code, 400)

    def test_post_userrequest_missing_data(self):
        bad_data = self.generic_payload.copy()
        del bad_data['requests']
        response = self.client.post(reverse('api:user_requests-list'), data=bad_data)
        self.assertEqual(response.status_code, 400)

    def test_post_userrequest_no_molecules(self):
        bad_data = self.generic_payload.copy()
        bad_data['requests'][0]['molecules'] = []
        response = self.client.post(reverse('api:user_requests-list'), data=bad_data)
        self.assertEqual(response.status_code, 400)

    def test_post_userrequest_no_requests(self):
        bad_data = self.generic_payload.copy()
        bad_data['requests'] = []
        response = self.client.post(reverse('api:user_requests-list'), data=bad_data)
        self.assertEqual(response.status_code, 400)

    def test_post_userrequest_no_time_allocation_for_instrument(self):
        bad_data = self.generic_payload.copy()
        bad_data['requests'][0]['location']['telescope_class'] = '2m0'
        bad_data['requests'][0]['molecules'][0]['telescope_name'] = '2M0-FLOYDS-SCICAM'
        response = self.client.post(reverse('api:user_requests-list'), data=bad_data)
        self.assertEqual(response.status_code, 400)
        self.assertIn('You do not have sufficient time', str(response.content))

    def test_post_userrequest_not_enough_time_allocation_for_instrument(self):
        bad_data = self.generic_payload.copy()
        self.time_allocation_1m0.std_time_used = 99.99
        self.time_allocation_1m0.save()
        response = self.client.post(reverse('api:user_requests-list'), data=bad_data)
        self.assertEqual(response.status_code, 400)
        self.assertIn('does not have enough time allocated', str(response.content))

    def test_post_userrequest_bad_ipp(self):
        bad_data = self.generic_payload.copy()
        bad_data['ipp_value'] = 0.0
        response = self.client.post(reverse('api:user_requests-list'), data=bad_data)
        self.assertEqual(response.status_code, 400)

    def test_post_userrequest_default_acquire_mode(self):
        bad_data = self.generic_payload.copy()
        # verify default acquire mode is 'optional' for non-floyds
        response = self.client.post(reverse('api:user_requests-list'), data=bad_data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['requests'][0]['target']['acquire_mode'], 'OPTIONAL')

        # check that default acquire mode is 'on' for floyds
        bad_data['requests'][0]['molecules'][0]['instrument_name'] = '2M0-FLOYDS-SCICAM'
        response = self.client.post(reverse('api:user_requests-list'), data=bad_data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['requests'][0]['target']['acquire_mode'], 'ON')

    def test_post_userrequest_single_must_have_one_request(self):
        bad_data = self.generic_payload.copy()
        bad_data['requests'].append(bad_data['requests'][0].copy())
        response = self.client.post(reverse('api:user_requests-list'), data=bad_data)
        self.assertEqual(response.status_code, 400)
        self.assertIn('must have exactly one child request', str(response.content))

    def test_post_userrequest_and_must_have_greater_than_one_request(self):
        bad_data = self.generic_payload.copy()
        bad_data['operator'] = 'AND'
        response = self.client.post(reverse('api:user_requests-list'), data=bad_data)
        self.assertEqual(response.status_code, 400)
        self.assertIn('must have more than one child request', str(response.content))

    def test_post_userrequest_constraints_optional(self):
        good_data = self.generic_payload.copy()
        del good_data['requests'][0]['constraints']['max_airmass']
        del good_data['requests'][0]['constraints']['min_lunar_distance']
        response = self.client.post(reverse('api:user_requests-list'), data=good_data)
        self.assertEqual(response.status_code, 201)

    def test_validation(self):
        good_data = self.generic_payload.copy()
        response = self.client.post(reverse('api:user_requests-validate'), data=good_data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['errors'])

    def test_validation_fail(self):
        bad_data = self.generic_payload.copy()
        del bad_data['operator']
        response = self.client.post(reverse('api:user_requests-validate'), data=bad_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['errors']['operator'][0], 'This field is required.')


class TestUserRequestIPP(ConfigDBTestMixin, SetTimeMixin, APITestCase):
    def setUp(self):
        super().setUp()
        self.proposal = mixer.blend(Proposal)
        self.user = mixer.blend(User)
        self.client.force_login(self.user)

        mixer.blend(Membership, user=self.user, proposal=self.proposal)

        semester = mixer.blend(
            Semester,
            id='2016B',
            start=datetime(2016, 9, 1, tzinfo=timezone.utc),
            end=datetime(2016, 12, 31, tzinfo=timezone.utc)
        )

        self.time_allocation_1m0 = mixer.blend(
            TimeAllocation, proposal=self.proposal, semester=semester,
            telescope_class='1m0', std_allocation=100.0, std_time_used=0.0,
            too_allocation=10, too_time_used=0.0, ipp_limit=10.0,
            ipp_time_available=5.0
        )

        self.time_allocation_2m0 = mixer.blend(
            TimeAllocation, proposal=self.proposal, semester=semester,
            telescope_class='2m0', std_allocation=100.0, std_time_used=0.0,
            too_allocation=10, too_time_used=0.0, ipp_limit=10.0,
            ipp_time_available=5.0
        )

        self.generic_payload = copy.deepcopy(generic_payload)
        self.generic_payload['ipp_value'] = 1.5
        self.generic_payload['proposal'] = self.proposal.id
        self.generic_payload['group_id'] = 'ipp_request'

        self.generic_multi_payload = copy.deepcopy(self.generic_payload)
        self.second_request = copy.deepcopy(generic_payload['requests'][0])
        self.second_request['molecules'][0]['instrument_name'] = '2M0-FLOYDS-SCICAM'
        self.second_request['location']['telescope_class'] = '2m0'
        self.generic_multi_payload['requests'].append(self.second_request)

    def _build_user_request(self, ur_dict):
        response = self.client.post(reverse('api:user_requests-list'), data=ur_dict)
        self.assertEqual(response.status_code, 201)

        return UserRequest.objects.get(group_id=ur_dict['group_id'])

    def test_user_request_debit_ipp_on_creation(self):
        self.assertEqual(self.time_allocation_1m0.ipp_time_available, 5.0)

        ur = self.generic_payload.copy()
        response = self.client.post(reverse('api:user_requests-list'), data=ur)
        self.assertEqual(response.status_code, 201)

        # verify that now that the object is saved, ipp has been debited
        time_allocation = TimeAllocation.objects.get(pk=self.time_allocation_1m0.id)
        self.assertLess(time_allocation.ipp_time_available, 5.0)

    def test_user_request_credit_ipp_on_cancelation(self):
        user_request = self._build_user_request(self.generic_payload.copy())
        # verify that now that the TimeAllocation has been debited
        time_allocation = TimeAllocation.objects.get(pk=self.time_allocation_1m0.id)
        self.assertLess(time_allocation.ipp_time_available, 5.0)
        user_request.state = 'CANCELED'
        user_request.save()
        # verify that now that the TimeAllocation has its original ipp value
        time_allocation = TimeAllocation.objects.get(pk=self.time_allocation_1m0.id)
        self.assertEqual(time_allocation.ipp_time_available, 5.0)
        # also verify that the child request state has changed to window_expired as well
        self.assertEqual(user_request.requests.first().state, 'CANCELED')

    def test_user_request_credit_ipp_on_expiration(self):
        user_request = self._build_user_request(self.generic_payload.copy())
        # verify that now that the TimeAllocation has been debited
        time_allocation = TimeAllocation.objects.get(pk=self.time_allocation_1m0.id)
        self.assertLess(time_allocation.ipp_time_available, 5.0)
        user_request.state = 'WINDOW_EXPIRED'
        user_request.save()
        # verify that now that the TimeAllocation has its original ipp value
        time_allocation = TimeAllocation.objects.get(pk=self.time_allocation_1m0.id)
        self.assertEqual(time_allocation.ipp_time_available, 5.0)
        # also verify that the child request state has changed to window_expired as well
        self.assertEqual(user_request.requests.first().state, 'WINDOW_EXPIRED')

    def test_user_request_debit_ipp_on_creation_fail(self):
        self.assertEqual(self.time_allocation_1m0.ipp_time_available, 5.0)

        ur = self.generic_payload.copy()
        # ipp value that is too high, will be rejected
        ur['ipp_value'] = 100.0
        response = self.client.post(reverse('api:user_requests-list'), data=ur)
        self.assertEqual(response.status_code, 400)
        self.assertIn('TimeAllocationError', str(response.content))

        # verify that objects were not created by the send
        self.assertFalse(UserRequest.objects.filter(group_id='ipp_request').exists())

    def test_user_request_multi_credit_ipp_back_on_cancelation(self):
        ur = self.generic_multi_payload
        ur['operator'] = 'MANY'
        user_request = self._build_user_request(ur)
        # verify that now that both the TimeAllocation has been debited
        time_allocation_1m0 = TimeAllocation.objects.get(pk=self.time_allocation_1m0.id)
        self.assertLess(time_allocation_1m0.ipp_time_available, 5.0)
        time_allocation_2m0 = TimeAllocation.objects.get(pk=self.time_allocation_2m0.id)
        self.assertLess(time_allocation_2m0.ipp_time_available, 5.0)
        # now set one request to completed, then set the user request to unschedulable
        request = user_request.requests.first()
        request.state = 'COMPLETED'
        request.save()
        user_request.state = 'WINDOW_EXPIRED'
        user_request.save()
        # now verify that time allocation 1 is still debited, but time allocation 2 has been credited back its time
        time_allocation_1m0 = TimeAllocation.objects.get(pk=self.time_allocation_1m0.id)
        self.assertLess(time_allocation_1m0.ipp_time_available, 5.0)
        time_allocation_2m0 = TimeAllocation.objects.get(pk=self.time_allocation_2m0.id)
        self.assertEqual(time_allocation_2m0.ipp_time_available, 5.0)


class TestRequestIPP(ConfigDBTestMixin, SetTimeMixin, APITestCase):
    def setUp(self):
        super().setUp()
        self.proposal = mixer.blend(Proposal)
        self.user = mixer.blend(User)
        self.client.force_login(self.user)

        mixer.blend(Membership, user=self.user, proposal=self.proposal)

        semester = mixer.blend(
            Semester,
            id='2016B',
            start=datetime(2016, 9, 1, tzinfo=timezone.utc),
            end=datetime(2016, 12, 31, tzinfo=timezone.utc)
        )

        self.time_allocation_1m0 = mixer.blend(
            TimeAllocation, proposal=self.proposal, semester=semester,
            telescope_class='1m0', std_allocation=100.0, std_time_used=0.0,
            too_allocation=10, too_time_used=0.0, ipp_limit=10.0,
            ipp_time_available=5.0
        )

        self.generic_payload = copy.deepcopy(generic_payload)
        self.generic_payload['ipp_value'] = 1.5
        self.generic_payload['proposal'] = self.proposal.id
        self.generic_payload['group_id'] = 'ipp_request'

    def _build_user_request(self, ur_dict):
        response = self.client.post(reverse('api:user_requests-list'), data=ur_dict)
        self.assertEqual(response.status_code, 201)

        return UserRequest.objects.get(group_id=ur_dict['group_id'])

    def test_request_debit_on_completion_after_expired(self):
        user_request = self._build_user_request(self.generic_payload.copy())
        # verify that now that the TimeAllocation has been debited
        time_allocation = TimeAllocation.objects.get(pk=self.time_allocation_1m0.id)
        debitted_ipp_value = time_allocation.ipp_time_available
        self.assertLess(debitted_ipp_value, 5.0)
        # now change requests state to expired
        request = user_request.requests.first()
        request.state = 'WINDOW_EXPIRED'
        request.save()
        # verify that now that the TimeAllocation has its original ipp value
        time_allocation = TimeAllocation.objects.get(pk=self.time_allocation_1m0.id)
        self.assertEqual(time_allocation.ipp_time_available, 5.0)
        # now set request to completed and see that ipp is debited once more
        request.state = 'COMPLETED'
        request.save()
        time_allocation = TimeAllocation.objects.get(pk=self.time_allocation_1m0.id)
        self.assertEqual(time_allocation.ipp_time_available, debitted_ipp_value)

    @patch('valhalla.userrequests.state_changes.logger')
    def test_request_debit_on_completion_after_expired_not_enough_time(self, mock_logger):
        user_request = self._build_user_request(self.generic_payload.copy())
        # verify that now that the TimeAllocation has been debited
        time_allocation = TimeAllocation.objects.get(pk=self.time_allocation_1m0.id)
        debitted_ipp_value = time_allocation.ipp_time_available
        self.assertLess(debitted_ipp_value, 5.0)
        # now change requests state to expired
        request = user_request.requests.first()
        request.state = 'WINDOW_EXPIRED'
        request.save()
        # verify that now that the TimeAllocation has its original ipp value
        time_allocation = TimeAllocation.objects.get(pk=self.time_allocation_1m0.id)
        self.assertEqual(time_allocation.ipp_time_available, 5.0)
        # set the time allocation available to 0.01, then set to completed
        time_allocation.ipp_time_available = 0.01
        time_allocation.save()
        # now set request to completed and see that ipp debitted to 0
        request.state = 'COMPLETED'
        request.save()
        time_allocation = TimeAllocation.objects.get(pk=self.time_allocation_1m0.id)
        self.assertEqual(time_allocation.ipp_time_available, 0)
        # test that the log message was generated
        self.assertIn('Time available after debiting will be capped at 0',
                      mock_logger.warn.call_args[0][0])

    def test_request_credit_back_on_cancelation(self):
        user_request = self._build_user_request(self.generic_payload.copy())
        # verify that now that the TimeAllocation has been debited
        time_allocation = TimeAllocation.objects.get(pk=self.time_allocation_1m0.id)
        self.assertLess(time_allocation.ipp_time_available, 5.0)
        # now change requests state to canceled
        request = user_request.requests.first()
        request.state = 'CANCELED'
        request.save()
        # verify that now that the TimeAllocation has its original ipp value
        time_allocation = TimeAllocation.objects.get(pk=self.time_allocation_1m0.id)
        self.assertEqual(time_allocation.ipp_time_available, 5.0)

    def test_request_credit_on_completion(self):
        payload = self.generic_payload.copy()
        payload['ipp_value'] = 0.5
        user_request = self._build_user_request(payload)
        # verify that now that the TimeAllocation has been debited
        time_allocation = TimeAllocation.objects.get(pk=self.time_allocation_1m0.id)
        self.assertEqual(time_allocation.ipp_time_available, 5.0)
        # now change requests state to canceled
        request = user_request.requests.first()
        request.state = 'COMPLETED'
        request.save()
        # verify that now that the TimeAllocation has its original ipp value
        time_allocation = TimeAllocation.objects.get(pk=self.time_allocation_1m0.id)
        self.assertGreater(time_allocation.ipp_time_available, 5.0)


class TestWindowApi(ConfigDBTestMixin, APITestCase):
    def setUp(self):
        super().setUp()
        self.proposal = mixer.blend(Proposal)
        self.user = mixer.blend(User)
        self.client.force_login(self.user)

        mixer.blend(Membership, user=self.user, proposal=self.proposal)
        self.generic_payload = copy.deepcopy(generic_payload)
        self.generic_payload['proposal'] = self.proposal.id

    def test_post_userrequest_window_end_before_start(self):
        bad_data = self.generic_payload.copy()
        bad_data['requests'][0]['windows'][0]['end'] = '2016-09-28T21:12:18Z'
        response = self.client.post(reverse('api:user_requests-list'), data=bad_data)
        self.assertEqual(response.status_code, 400)

    def test_post_userrequest_no_windows_invalid(self):
        bad_data = self.generic_payload.copy()
        bad_data['requests'][0]['windows'] = []
        response = self.client.post(reverse('api:user_requests-list'), data=bad_data)
        self.assertEqual(response.status_code, 400)
        bad_data = self.generic_payload.copy()
        del bad_data['requests'][0]['windows']
        response = self.client.post(reverse('api:user_requests-list'), data=bad_data)
        self.assertEqual(response.status_code, 400)


class TestCadenceApi(ConfigDBTestMixin, SetTimeMixin, APITestCase):
    def setUp(self):
        super().setUp()

        self.proposal = mixer.blend(Proposal)
        self.user = mixer.blend(User)
        mixer.blend(Membership, user=self.user, proposal=self.proposal)
        semester = mixer.blend(
            Semester, id='2016B', start=datetime(2016, 9, 1, tzinfo=timezone.utc),
            end=datetime(2016, 12, 31, tzinfo=timezone.utc)
        )
        self.time_allocation_1m0 = mixer.blend(
            TimeAllocation, proposal=self.proposal, semester=semester,
            telescope_class='1m0', std_allocation=100.0, std_time_used=0.0,
            too_allocation=10, too_time_used=0.0, ipp_limit=10.0,
            ipp_time_available=5.0
        )

        self.client.force_login(self.user)

        self.generic_payload = copy.deepcopy(generic_payload)
        self.generic_payload['proposal'] = self.proposal.id
        self.generic_payload['requests'][0]['windows'] = []
        self.generic_payload['requests'][0]['cadence'] = {
            'start': '2016-09-01T21:12:18Z',
            'end': '2016-09-03T22:12:19Z',
            'period': 24.0,
            'jitter': 12.0
        }

    def test_post_userrequest_cadence_and_windows_is_invalid(self):
        bad_data = self.generic_payload.copy()
        bad_data['windows'] = [{'start': '2016-09-29T21:12:18Z', 'end': '2016-10-29T21:12:19Z'}]
        response = self.client.post(reverse('api:user_requests-list'), data=bad_data)
        self.assertEqual(response.status_code, 400)
        self.assertTrue(response.json()['requests'][0]['cadence'])

    def test_post_userrequest_cadence_is_invalid(self):
        bad_data = self.generic_payload.copy()
        bad_data['windows'] = []
        response = self.client.post(reverse('api:user_requests-list'), data=bad_data)
        self.assertEqual(response.status_code, 400)
        del bad_data['windows']
        response = self.client.post(reverse('api:user_requests-list'), data=bad_data)
        self.assertEqual(response.status_code, 400)

    def test_post_cadence_end_before_start_invalid(self):
        bad_data = self.generic_payload.copy()
        end = bad_data['requests'][0]['cadence']['end']
        bad_data['requests'][0]['cadence']['end'] = bad_data['requests'][0]['cadence']['start']
        bad_data['requests'][0]['cadence']['start'] = end
        response = self.client.post(reverse('api:user_requests-cadence'), data=bad_data)
        self.assertEqual(response.status_code, 400)
        self.assertIn('cannot be earlier than cadence start', str(response.content))

    def test_post_cadence_valid(self):
        response = self.client.post(reverse('api:user_requests-cadence'), data=self.generic_payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['requests']), 2)

    def test_cadence_invalid(self):
        bad_data = self.generic_payload.copy()
        bad_data['requests'][0]['cadence']['jitter'] = 'bug'
        response = self.client.post(reverse('api:user_requests-cadence'), data=bad_data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['cadence']['jitter'], ['A valid number is required.'])

    def test_cadence_invalid_period(self):
        bad_data = self.generic_payload.copy()
        bad_data['requests'][0]['cadence']['period'] = -666
        response = self.client.post(reverse('api:user_requests-cadence'), data=bad_data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['cadence']['period'], ['Ensure this value is greater than or equal to 0.02.'])

    def test_post_userrequest_after_valid_cadence(self):
        response = self.client.post(reverse('api:user_requests-cadence'), data=self.generic_payload)
        second_response = self.client.post(reverse('api:user_requests-list'), data=response.json())
        self.assertEqual(second_response.status_code, 201)
        self.assertGreater(self.user.userrequest_set.all().count(), 0)


class TestSiderealTarget(ConfigDBTestMixin, SetTimeMixin, APITestCase):
    def setUp(self):
        super().setUp()
        self.proposal = mixer.blend(Proposal)
        self.user = mixer.blend(User)
        self.client.force_login(self.user)

        semester = mixer.blend(Semester, id='2016B', start=datetime(2016, 9, 1, tzinfo=timezone.utc),
                               end=datetime(2016, 12, 31, tzinfo=timezone.utc)
                               )
        self.time_allocation_1m0 = mixer.blend(TimeAllocation, proposal=self.proposal, semester=semester,
                                               telescope_class='1m0', std_allocation=100.0, std_time_used=0.0,
                                               too_allocation=10, too_time_used=0.0, ipp_limit=10.0,
                                               ipp_time_available=5.0
                                               )

        mixer.blend(Membership, user=self.user, proposal=self.proposal)
        self.generic_payload = copy.deepcopy(generic_payload)
        self.generic_payload['proposal'] = self.proposal.id

    def test_post_userrequest_no_ra(self):
        bad_data = self.generic_payload.copy()
        del bad_data['requests'][0]['target']['ra']
        response = self.client.post(reverse('api:user_requests-list'), data=bad_data)
        self.assertEqual(response.status_code, 400)
        self.assertIn('ra', str(response.content))

    def test_post_userrequest_extra_ns_field(self):
        bad_data = self.generic_payload.copy()
        bad_data['requests'][0]['target']['longascnode'] = 4.0
        response = self.client.post(reverse('api:user_requests-list'), data=bad_data)
        self.assertEqual(response.status_code, 201)
        target = response.json()['requests'][0]['target']
        self.assertNotIn('longascnode', target)

    def test_post_userrequest_test_defaults(self):
        bad_data = self.generic_payload.copy()
        response = self.client.post(reverse('api:user_requests-list'), data=bad_data)
        self.assertEqual(response.status_code, 201)
        target = response.json()['requests'][0]['target']
        self.assertEqual(target['proper_motion_ra'], 0.0)
        self.assertEqual(target['proper_motion_dec'], 0.0)
        self.assertEqual(target['parallax'], 0.0)
        self.assertEqual(target['coordinate_system'], 'ICRS')
        self.assertEqual(target['equinox'], 'J2000')
        self.assertEqual(target['epoch'], 2000.0)

    def test_post_userrequest_test_proper_motion_no_epoch(self):
        bad_data = self.generic_payload.copy()
        bad_data['requests'][0]['target']['proper_motion_ra'] = 1.0
        bad_data['requests'][0]['target']['proper_motion_dec'] = 1.0
        # epoch defaults to 2000 so we should pass
        response = self.client.post(reverse('api:user_requests-list'), data=bad_data)
        self.assertEqual(response.status_code, 201)

    def test_post_userrequest_test_proper_motion_with_epoch(self):
        bad_data = self.generic_payload.copy()
        bad_data['requests'][0]['target']['proper_motion_ra'] = 1.0
        bad_data['requests'][0]['target']['proper_motion_dec'] = 1.0
        bad_data['requests'][0]['target']['epoch'] = 2001.0
        response = self.client.post(reverse('api:user_requests-list'), data=bad_data)
        self.assertEqual(response.status_code, 201)


class TestNonSiderealTarget(ConfigDBTestMixin, SetTimeMixin, APITestCase):
    def setUp(self):
        super().setUp()
        self.proposal = mixer.blend(Proposal)
        self.user = mixer.blend(User)
        self.client.force_login(self.user)

        semester = mixer.blend(Semester, id='2016B', start=datetime(2016, 9, 1, tzinfo=timezone.utc),
                               end=datetime(2016, 12, 31, tzinfo=timezone.utc))
        self.time_allocation_1m0 = mixer.blend(TimeAllocation, proposal=self.proposal, semester=semester,
                                               telescope_class='1m0', std_allocation=100.0, std_time_used=0.0,
                                               too_allocation=10, too_time_used=0.0, ipp_limit=10.0,
                                               ipp_time_available=5.0)

        mixer.blend(Membership, user=self.user, proposal=self.proposal)
        self.generic_payload = copy.deepcopy(generic_payload)
        self.generic_payload['proposal'] = self.proposal.id
        self.generic_payload['requests'][0]['target'] = {
            'name': 'fake target',
            'type': 'NON_SIDEREAL',
            'scheme': 'MPC_MINOR_PLANET',
            # Non sidereal param
            'epochofel': 57660.0,
            'orbinc': 9.7942900,
            'longascnode': 122.8943400,
            'argofperih': 78.3278300,
            'perihdist': 1.0,
            'meandist': 0.7701170,
            'meananom': 165.6860400,
            'eccentricity': 0.5391962,
            'epochofperih': 57400.0,
        }

    def test_post_userrequest_invalid_target_type(self):
        bad_data = self.generic_payload.copy()
        bad_data['requests'][0]['target']['type'] = 'NOTATYPE'
        response = self.client.post(reverse('api:user_requests-list'), data=bad_data)
        self.assertEqual(response.status_code, 400)

    def test_post_userrequest_non_sidereal_target(self):
        good_data = self.generic_payload.copy()

        response = self.client.post(reverse('api:user_requests-list'), data=good_data)
        self.assertEqual(response.status_code, 201)

    def test_post_userrequest_non_comet_eccentricity(self):
        bad_data = self.generic_payload.copy()
        bad_data['requests'][0]['target']['eccentricity'] = 0.99

        response = self.client.post(reverse('api:user_requests-list'), data=bad_data)
        self.assertEqual(response.status_code, 400)
        self.assertIn('requires eccentricity to be lower', str(response.content))

    def test_post_userrequest_non_sidereal_mpc_comet(self):
        good_data = self.generic_payload.copy()
        good_data['requests'][0]['target']['eccentricity'] = 0.99
        good_data['requests'][0]['target']['scheme'] = 'MPC_COMET'
        response = self.client.post(reverse('api:user_requests-list'), data=good_data)
        self.assertEqual(response.status_code, 201)

    def test_post_userrequest_non_sidereal_not_visible(self):
        bad_data = self.generic_payload.copy()
        bad_data['requests'][0]['target']['eccentricity'] = 0.99
        bad_data['requests'][0]['target']['scheme'] = 'MPC_COMET'
        bad_data['requests'][0]['target']['perihdist'] = 5.0

        response = self.client.post(reverse('api:user_requests-list'), data=bad_data)
        self.assertEqual(response.status_code, 400)
        self.assertIn('did not fit into any visible intervals', str(response.content))

    def test_post_userrequest_non_sidereal_missing_fields(self):
        bad_data = self.generic_payload.copy()
        del bad_data['requests'][0]['target']['eccentricity']
        del bad_data['requests'][0]['target']['meandist']

        response = self.client.post(reverse('api:user_requests-list'), data=bad_data)
        self.assertEqual(response.status_code, 400)
        self.assertIn('eccentricity', str(response.content))
        self.assertIn('meandist', str(response.content))


class TestSatelliteTarget(ConfigDBTestMixin, SetTimeMixin, APITestCase):
    def setUp(self):
        super().setUp()
        self.proposal = mixer.blend(Proposal)
        self.user = mixer.blend(User)
        self.client.force_login(self.user)

        semester = mixer.blend(Semester, id='2016B', start=datetime(2016, 9, 1, tzinfo=timezone.utc),
                               end=datetime(2016, 12, 31, tzinfo=timezone.utc))

        self.time_allocation_1m0 = mixer.blend(TimeAllocation, proposal=self.proposal, semester=semester,
                                               telescope_class='1m0', std_allocation=100.0, std_time_used=0.0,
                                               too_allocation=10, too_time_used=0.0, ipp_limit=10.0,
                                               ipp_time_available=5.0)

        mixer.blend(Membership, user=self.user, proposal=self.proposal)
        self.generic_payload = copy.deepcopy(generic_payload)
        self.generic_payload['proposal'] = self.proposal.id
        self.generic_payload['requests'][0]['target'] = {
            'name': 'fake target',
            'type': 'SATELLITE',
            # satellite
            'altitude': 33.0,
            'azimuth': 2.0,
            'diff_pitch_rate': 3.0,
            'diff_roll_rate': 4.0,
            'diff_pitch_acceleration': 5.0,
            'diff_roll_acceleration': 0.99,
            'diff_epoch_rate': 22.0,
            'epoch': 2000.0,
        }

    def test_post_userrequest_satellite_target(self):
        good_data = self.generic_payload.copy()
        response = self.client.post(reverse('api:user_requests-list'), data=good_data)
        self.assertEqual(response.status_code, 201)

    def test_post_userrequest_satellite_missing_fields(self):
        bad_data = self.generic_payload.copy()
        del bad_data['requests'][0]['target']['diff_epoch_rate']
        del bad_data['requests'][0]['target']['diff_pitch_acceleration']

        response = self.client.post(reverse('api:user_requests-list'), data=bad_data)
        self.assertEqual(response.status_code, 400)
        self.assertIn('diff_epoch_rate', str(response.content))
        self.assertIn('diff_pitch_acceleration', str(response.content))


class TestLocationApi(ConfigDBTestMixin, SetTimeMixin, APITestCase):
    def setUp(self):
        super().setUp()
        self.proposal = mixer.blend(Proposal)
        self.user = mixer.blend(User)
        self.client.force_login(self.user)

        semester = mixer.blend(Semester, id='2016B', start=datetime(2016, 9, 1, tzinfo=timezone.utc),
                               end=datetime(2016, 12, 31, tzinfo=timezone.utc))

        self.time_allocation_1m0 = mixer.blend(TimeAllocation, proposal=self.proposal, semester=semester,
                                               telescope_class='1m0', std_allocation=100.0, std_time_used=0.0,
                                               too_allocation=10, too_time_used=0.0, ipp_limit=10.0,
                                               ipp_time_available=5.0)

        mixer.blend(Membership, user=self.user, proposal=self.proposal)
        self.generic_payload = copy.deepcopy(generic_payload)
        self.generic_payload['proposal'] = self.proposal.id

    def test_post_userrequest_all_location_info(self):
        good_data = self.generic_payload.copy()
        good_data['requests'][0]['location']['site'] = 'tst'
        good_data['requests'][0]['location']['observatory'] = 'doma'
        good_data['requests'][0]['location']['telescope'] = '1m0a'
        response = self.client.post(reverse('api:user_requests-list'), data=good_data)
        self.assertEqual(response.status_code, 201)

    def test_post_userrequest_observatory_no_site(self):
        good_data = self.generic_payload.copy()
        good_data['requests'][0]['location']['observatory'] = 'doma'
        good_data['requests'][0]['location']['telescope'] = '1m0a'
        response = self.client.post(reverse('api:user_requests-list'), data=good_data)
        self.assertEqual(response.status_code, 400)

    def test_post_userrequest_observatory_no_observatory(self):
        good_data = self.generic_payload.copy()
        good_data['requests'][0]['location']['site'] = 'tst'
        good_data['requests'][0]['location']['telescope'] = '1m0a'
        response = self.client.post(reverse('api:user_requests-list'), data=good_data)
        self.assertEqual(response.status_code, 400)

    def test_post_userrequest_observatory_bad_observatory(self):
        bad_data = self.generic_payload.copy()
        bad_data['requests'][0]['location']['site'] = 'tst'
        bad_data['requests'][0]['location']['observatory'] = 'domx'
        bad_data['requests'][0]['location']['telescope'] = '1m0a'
        response = self.client.post(reverse('api:user_requests-list'), data=bad_data)
        self.assertEqual(response.status_code, 400)

    def test_post_userrequest_observatory_bad_site(self):
        bad_data = self.generic_payload.copy()
        bad_data['requests'][0]['location']['site'] = 'bpl'
        bad_data['requests'][0]['location']['observatory'] = 'doma'
        bad_data['requests'][0]['location']['telescope'] = '1m0a'
        response = self.client.post(reverse('api:user_requests-list'), data=bad_data)
        self.assertEqual(response.status_code, 400)

    def test_post_userrequest_observatory_bad_telescope(self):
        bad_data = self.generic_payload.copy()
        bad_data['requests'][0]['location']['site'] = 'tst'
        bad_data['requests'][0]['location']['observatory'] = 'doma'
        bad_data['requests'][0]['location']['telescope'] = '1m0b'
        response = self.client.post(reverse('api:user_requests-list'), data=bad_data)
        self.assertEqual(response.status_code, 400)


class TestMoleculeApi(ConfigDBTestMixin, SetTimeMixin, APITestCase):
    def setUp(self):
        super().setUp()
        self.proposal = mixer.blend(Proposal)
        self.user = mixer.blend(User)
        self.client.force_login(self.user)

        semester = mixer.blend(Semester, id='2016B', start=datetime(2016, 9, 1, tzinfo=timezone.utc),
                               end=datetime(2016, 12, 31, tzinfo=timezone.utc))
        self.time_allocation_1m0 = mixer.blend(TimeAllocation, proposal=self.proposal, semester=semester,
                                               telescope_class='1m0', std_allocation=100.0, std_time_used=0.0,
                                               too_allocation=10, too_time_used=0.0, ipp_limit=10.0,
                                               ipp_time_available=5.0)

        mixer.blend(Membership, user=self.user, proposal=self.proposal)
        self.generic_payload = copy.deepcopy(generic_payload)
        self.generic_payload['proposal'] = self.proposal.id
        self.extra_molecule = copy.deepcopy(self.generic_payload['requests'][0]['molecules'][0])

    def test_default_ag_mode_for_spectrograph(self):
        good_data = self.generic_payload.copy()
        response = self.client.post(reverse('api:user_requests-list'), data=good_data)
        self.assertEqual(response.status_code, 201)
        molecule = response.json()['requests'][0]['molecules'][0]
        # check that without spectral instrument, these defaults are different
        self.assertEqual(molecule['ag_mode'], 'OPTIONAL')
        self.assertEqual(molecule['spectra_slit'], '')

        good_data['requests'][0]['molecules'][0]['instrument_name'] = '2M0-FLOYDS-SCICAM'
        response = self.client.post(reverse('api:user_requests-list'), data=good_data)
        self.assertEqual(response.status_code, 201)
        molecule = response.json()['requests'][0]['molecules'][0]
        # now with spectral instrument, defaults have changed
        self.assertEqual(molecule['ag_mode'], 'ON')
        self.assertEqual(molecule['spectra_slit'], 'floyds_slit_default')

    def test_invalid_filter_for_instrument(self):
        bad_data = self.generic_payload.copy()
        bad_data['requests'][0]['molecules'][0]['filter'] = 'magic'
        response = self.client.post(reverse('api:user_requests-list'), data=bad_data)
        self.assertIn('Invalid filter', str(response.content))
        self.assertEqual(response.status_code, 400)

    def test_filter_not_necessary_for_type(self):
        good_data = self.generic_payload.copy()
        good_data['requests'][0]['molecules'][0]['type'] = 'ARC'
        del good_data['requests'][0]['molecules'][0]['filter']
        response = self.client.post(reverse('api:user_requests-list'), data=good_data)
        self.assertEqual(response.status_code, 201)

    def test_invalid_spectra_slit_for_instrument(self):
        bad_data = self.generic_payload.copy()
        bad_data['requests'][0]['molecules'][0]['instrument_name'] = '2M0-FLOYDS-SCICAM'
        del bad_data['requests'][0]['molecules'][0]['filter']
        bad_data['requests'][0]['molecules'][0]['spectra_slit'] = 'slit_really_small'
        response = self.client.post(reverse('api:user_requests-list'), data=bad_data)
        self.assertIn('Invalid spectra slit', str(response.content))
        self.assertEqual(response.status_code, 400)

    def test_invalid_binning_for_instrument(self):
        bad_data = self.generic_payload.copy()
        bad_data['requests'][0]['molecules'][0]['bin_x'] = 5
        bad_data['requests'][0]['molecules'][0]['bin_y'] = 5
        response = self.client.post(reverse('api:user_requests-list'), data=bad_data)
        self.assertIn('Invalid binning', str(response.content))
        self.assertEqual(response.status_code, 400)

    def test_default_binning_for_instrument(self):
        good_data = self.generic_payload.copy()
        del good_data['requests'][0]['molecules'][0]['bin_x']
        del good_data['requests'][0]['molecules'][0]['bin_y']
        response = self.client.post(reverse('api:user_requests-list'), data=good_data)
        self.assertEqual(response.status_code, 201)
        molecule = response.json()['requests'][0]['molecules'][0]
        self.assertEqual(molecule['bin_x'], 2)
        self.assertEqual(molecule['bin_y'], 2)

    def test_must_set_both_binnings(self):
        bad_data = self.generic_payload.copy()
        del bad_data['requests'][0]['molecules'][0]['bin_x']
        response = self.client.post(reverse('api:user_requests-list'), data=bad_data)
        self.assertIn('Missing one of bin_x or bin_y', str(response.content))
        self.assertEqual(response.status_code, 400)

    def test_request_invalid_instrument_name(self):
        bad_data = self.generic_payload.copy()
        bad_data['requests'][0]['molecules'][0]['instrument_name'] = 'FAKE-INSTRUMENT'
        response = self.client.post(reverse('api:user_requests-list'), data=bad_data)
        self.assertIn('Invalid instrument name', str(response.content))
        self.assertEqual(response.status_code, 400)

    def test_request_invalid_instrument_name_for_location(self):
        bad_data = self.generic_payload.copy()
        bad_data['requests'][0]['location']['site'] = 'non'
        response = self.client.post(reverse('api:user_requests-list'), data=bad_data)
        self.assertIn("Invalid instrument name \\\'1M0-SCICAM-SBIG\\\' at site", str(response.content))
        self.assertEqual(response.status_code, 400)

    def test_molecules_with_different_instrument_names(self):
        bad_data = self.generic_payload.copy()
        bad_data['requests'][0]['molecules'].append(bad_data['requests'][0]['molecules'][0].copy())
        bad_data['requests'][0]['molecules'][1]['instrument_name'] = '2M0-FLOYDS-SCICAM'
        response = self.client.post(reverse('api:user_requests-list'), data=bad_data)
        self.assertIn('Each Molecule must specify the same instrument name', str(response.content))
        self.assertEqual(response.status_code, 400)

    def test_fill_window_on_more_than_one_molecule_fails(self):
        bad_data = self.generic_payload.copy()
        bad_data['requests'][0]['molecules'].append(self.extra_molecule.copy())
        bad_data['requests'][0]['molecules'][0]['fill_window'] = True
        bad_data['requests'][0]['molecules'][1]['fill_window'] = True
        response = self.client.post(reverse('api:user_requests-list'), data=bad_data)
        self.assertIn('Only one molecule can have `fill_window` set', str(response.content))
        self.assertEqual(response.status_code, 400)

    def test_fill_window_one_molecule_fills_the_window(self):
        good_data = self.generic_payload.copy()
        good_data['requests'][0]['molecules'][0]['fill_window'] = True
        initial_exposure_count = good_data['requests'][0]['molecules'][0]['exposure_count']
        response = self.client.post(reverse('api:user_requests-list'), data=good_data)
        ur = response.json()
        self.assertGreater(ur['requests'][0]['molecules'][0]['exposure_count'], initial_exposure_count)
        self.assertEqual(response.status_code, 201)

    def test_fill_window_two_molecules_one_false_fills_the_window(self):
        good_data = self.generic_payload.copy()
        good_data['requests'][0]['molecules'].append(self.extra_molecule.copy())
        good_data['requests'][0]['molecules'][0]['fill_window'] = True
        good_data['requests'][0]['molecules'][1]['fill_window'] = False
        initial_exposure_count = good_data['requests'][0]['molecules'][0]['exposure_count']
        response = self.client.post(reverse('api:user_requests-list'), data=good_data)
        ur = response.json()
        self.assertGreater(ur['requests'][0]['molecules'][0]['exposure_count'], initial_exposure_count)
        self.assertEqual(response.status_code, 201)

    def test_fill_window_two_molecules_one_blank_fills_the_window(self):
        good_data = self.generic_payload.copy()
        good_data['requests'][0]['molecules'].append(self.extra_molecule.copy())
        good_data['requests'][0]['molecules'][0]['fill_window'] = True
        initial_exposure_count = good_data['requests'][0]['molecules'][0]['exposure_count']
        response = self.client.post(reverse('api:user_requests-list'), data=good_data)
        ur = response.json()
        self.assertGreater(ur['requests'][0]['molecules'][0]['exposure_count'], initial_exposure_count)
        self.assertEqual(response.status_code, 201)

    def test_fill_window_two_molecules_first_fills_the_window(self):
        good_data = self.generic_payload.copy()
        good_data['requests'][0]['molecules'].append(self.extra_molecule.copy())
        good_data['requests'][0]['molecules'][0]['fill_window'] = True
        initial_exposure_count = good_data['requests'][0]['molecules'][0]['exposure_count']
        response = self.client.post(reverse('api:user_requests-list'), data=good_data)
        ur = response.json()
        self.assertGreater(ur['requests'][0]['molecules'][0]['exposure_count'], initial_exposure_count)
        self.assertEqual(response.status_code, 201)

    def test_fill_window_not_enough_time_fails(self):
        bad_data = self.generic_payload.copy()
        bad_data['requests'][0]['windows'][0] = {
            'start': '2016-09-29T21:12:18Z',
            'end': '2016-09-29T21:21:19Z'
        }
        bad_data['requests'][0]['molecules'][0]['fill_window'] = True
        response = self.client.post(reverse('api:user_requests-list'), data=bad_data)
        self.assertIn('did not fit into any visible intervals', str(response.content))
        self.assertEqual(response.status_code, 400)

    def test_fill_window_confined_window_fills_the_window(self):
        good_data = self.generic_payload.copy()
        good_data['requests'][0]['windows'][0] = {
            'start': '2016-09-29T23:12:18Z',
            'end': '2016-09-29T23:21:19Z'
        }
        good_data['requests'][0]['molecules'][0]['fill_window'] = True
        response = self.client.post(reverse('api:user_requests-list'), data=good_data)
        ur = response.json()
        self.assertEqual(ur['requests'][0]['molecules'][0]['exposure_count'], 3)
        self.assertEqual(response.status_code, 201)

    def test_fill_window_confined_window_2_fills_the_window(self):
        good_data = self.generic_payload.copy()
        good_data['requests'][0]['windows'][0] = {
            'start': '2016-09-29T23:12:18Z',
            'end': '2016-09-29T23:21:19Z'
        }
        good_data['requests'][0]['molecules'][0]['exposure_time'] = 50
        good_data['requests'][0]['molecules'][0]['fill_window'] = True
        response = self.client.post(reverse('api:user_requests-list'), data=good_data)
        ur = response.json()
        self.assertEqual(ur['requests'][0]['molecules'][0]['exposure_count'], 5)
        self.assertEqual(response.status_code, 201)


class TestGetRequestApi(ConfigDBTestMixin, APITestCase):
    def setUp(self):
        super().setUp()
        self.proposal = mixer.blend(Proposal)
        self.user = mixer.blend(User, is_staff=False, is_superuser=False)
        self.staff_user = mixer.blend(User, is_staff=True)
        mixer.blend(Membership, user=self.user, proposal=self.proposal)
        self.user_request = mixer.blend(UserRequest, submitter=self.user, proposal=self.proposal)

    def test_get_request_list_authenticated(self):
        request = mixer.blend(Request, user_request=self.user_request, observation_note='testobsnote')
        self.client.force_login(self.user)
        result = self.client.get(reverse('api:requests-list'))
        self.assertEquals(result.json()['results'][0]['observation_note'], request.observation_note)

    def test_get_request_list_unauthenticated(self):
        mixer.blend(Request, user_request=self.user_request, observation_note='testobsnote')
        result = self.client.get(reverse('api:requests-list'))
        self.assertNotContains(result, 'testobsnote')
        self.assertEquals(result.status_code, 200)

    def test_get_request_detail_authenticated(self):
        request = mixer.blend(Request, user_request=self.user_request, observation_note='testobsnote')
        self.client.force_login(self.user)
        result = self.client.get(reverse('api:requests-detail', args=(request.id,)))
        self.assertEquals(result.json()['observation_note'], request.observation_note)

    def test_get_request_detail_unauthenticated(self):
        request = mixer.blend(Request, user_request=self.user_request, observation_note='testobsnote')
        result = self.client.get(reverse('api:requests-detail', args=(request.id,)))
        self.assertEqual(result.status_code, 404)

    def test_get_request_list_staff(self):
        request = mixer.blend(Request, user_request=self.user_request, observation_note='testobsnote2')
        self.client.force_login(self.staff_user)
        result = self.client.get(reverse('api:requests-detail', args=(request.id,)))
        self.assertEquals(result.json()['observation_note'], request.observation_note)

    def test_get_request_detail_public(self):
        proposal = mixer.blend(Proposal, public=True)
        self.user_request.proposal = proposal
        self.user_request.save()
        request = mixer.blend(Request, user_request=self.user_request, observation_note='testobsnote2')
        self.client.logout()
        result = self.client.get(reverse('api:requests-detail', args=(request.id,)))
        self.assertEquals(result.json()['observation_note'], request.observation_note)


class TestBlocksApi(APITestCase):
    def setUp(self):
        self.proposal = mixer.blend(Proposal)
        self.user = mixer.blend(User, is_staff=False, is_superuser=False)
        self.staff_user = mixer.blend(User, is_staff=True)
        mixer.blend(Membership, user=self.user, proposal=self.proposal)
        self.user_request = mixer.blend(UserRequest, submitter=self.user, proposal=self.proposal)
        self.request = mixer.blend(Request, user_request=self.user_request)
        self.client.force_login(self.user)
        self.TESTDATA = os.path.join(os.path.dirname(__file__), 'data/blocks.json')

    @responses.activate
    def test_empty_blocks(self):
        responses.add(
            responses.GET,
            '{0}/pond/pond/block/request/{1}.json'.format(
                settings.POND_URL, self.request.get_id_display()
            ),
            body='[]',
            status=200
        )
        result = self.client.get(reverse('api:requests-blocks', args=(self.request.id,)))
        self.assertFalse(result.json())

    @responses.activate
    def test_block_returns(self):
        with open(self.TESTDATA) as f:
            responses.add(
                responses.GET,
                '{0}/pond/pond/block/request/{1}.json'.format(
                    settings.POND_URL, self.request.get_id_display()
                ),
                body=f.read(),
                status=200
            )
            result = self.client.get(reverse('api:requests-blocks', args=(self.request.id,)))
            self.assertEqual(len(result.json()), 251)

    @responses.activate
    def test_no_canceled(self):
        with open(self.TESTDATA) as f:
            responses.add(
                responses.GET,
                '{0}/pond/pond/block/request/{1}.json'.format(
                    settings.POND_URL, self.request.get_id_display()
                ),
                body=f.read(),
                status=200
            )
            result = self.client.get(reverse('api:requests-blocks', args=(self.request.id,)) + '?canceled=false')
            self.assertEqual(len(result.json()), 2)

    @patch('requests.get', side_effect=ConnectionError())
    def test_no_connection(self, request_patch):
        result = self.client.get(reverse('api:requests-blocks', args=(self.request.id,)))
        self.assertFalse(result.json())


class TestDraftUserRequestApi(APITestCase):
    def setUp(self):
        self.user = mixer.blend(User)
        self.proposal = mixer.blend(Proposal)
        mixer.blend(Membership, user=self.user, proposal=self.proposal)
        self.client.force_login(self.user)

    def test_unauthenticated(self):
        self.client.logout()
        response = self.client.get(reverse('api:drafts-list'))
        self.assertEqual(response.status_code, 403)

    def test_user_can_list_drafts(self):
        mixer.cycle(5).blend(DraftUserRequest, author=self.user, proposal=self.proposal)
        response = self.client.get(reverse('api:drafts-list'))
        self.assertContains(response, self.proposal.id)
        self.assertEqual(response.json()['count'], 5)

    def test_user_can_list_proposal_drafts(self):
        other_user = mixer.blend(User)
        mixer.blend(Membership, user=other_user, proposal=self.proposal)
        mixer.cycle(5).blend(DraftUserRequest, author=other_user, proposal=self.proposal)
        response = self.client.get(reverse('api:drafts-list'))
        self.assertContains(response, self.proposal.id)
        self.assertEqual(response.json()['count'], 5)

    def test_user_can_create_draft(self):
        data = {
            'proposal': self.proposal.id,
            'title': 'Test Draft',
            'content': '{"foo": "bar"}'
        }
        response = self.client.post(reverse('api:drafts-list'), data=data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['title'], data['title'])

    def test_post_invalid_json(self):
        data = {
            'proposal': self.proposal.id,
            'content': 'foo: bar'
        }
        response = self.client.post(reverse('api:drafts-list'), data=data)
        self.assertEqual(response.status_code, 400)
        self.assertIn('Content must be valid JSON', response.json()['content'])

    def test_post_wrong_proposal(self):
        other_proposal = mixer.blend(Proposal)
        data = {
            'proposal': other_proposal.id,
            'title': 'I cant do this',
            'content': '{"foo": "bar"}'
        }
        response = self.client.post(reverse('api:drafts-list'), data=data)
        self.assertEqual(response.status_code, 400)
        self.assertIn('You are not a member of that proposal', response.json()['non_field_errors'])

    def test_user_cannot_duplicate_draft(self):
        mixer.blend(DraftUserRequest, author=self.user, proposal=self.proposal, title='dup')
        data = {
            'proposal': self.proposal.id,
            'title': 'dup',
            'content': '{"foo": "bar"}'
        }
        response = self.client.post(reverse('api:drafts-list'), data=data)
        self.assertEqual(response.status_code, 400)
        self.assertIn('The fields author, proposal, title must make a unique set.', str(response.content))

    def test_user_can_update_draft(self):
        draft = mixer.blend(DraftUserRequest, author=self.user, proposal=self.proposal)
        data = {
            'proposal': self.proposal.id,
            'title': 'an updated draft',
            'content': '{"updated": true}'
        }
        response = self.client.put(reverse('api:drafts-detail', args=(draft.id,)), data=data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(DraftUserRequest.objects.get(id=draft.id).title, 'an updated draft')

    def test_user_can_delete_draft(self):
        draft = mixer.blend(DraftUserRequest, author=self.user, proposal=self.proposal)
        response = self.client.delete(reverse('api:drafts-detail', args=(draft.id,)))
        self.assertEqual(response.status_code, 204)

    def test_user_cannot_delete_other_draft(self):
        other_user = mixer.blend(User)
        other_proposal = mixer.blend(Proposal)
        draft = mixer.blend(DraftUserRequest, author=other_user, proposal=other_proposal)
        response = self.client.delete(reverse('api:drafts-detail', args=(draft.id,)))
        self.assertEqual(response.status_code, 404)


class TestAirmassApi(ConfigDBTestMixin, SetTimeMixin, APITestCase):
    def setUp(self):
        super().setUp()
        self.request = {
            'target': {
                'name': 'fake target',
                'type': 'SIDEREAL',
                'dec': 20,
                'ra': 34.4,
            },
            'molecules': [{
                'type': 'EXPOSE',
                'instrument_name': '1M0-SCICAM-SBIG',
                'filter': 'air',
                'exposure_time': 100,
                'exposure_count': 1,
                'bin_x': 1,
                'bin_y': 1,
            }],
            'windows': [{
                'start': '2016-09-29T21:12:18Z',
                'end': '2016-10-29T21:12:19Z'
            }],
            'location': {
                'telescope_class': '1m0',
            },
            'constraints': {
                'max_airmass': 2.0,
                'min_lunar_distance': 30.0,
            }
        }

    def test_airmass(self):
        response = self.client.post(reverse('api:airmass'), data=self.request)
        self.assertIn('tst', response.json()['airmass_data'])
        self.assertTrue(response.json()['airmass_data']['tst']['times'])


@patch('valhalla.userrequests.state_changes.modify_ipp_time_from_requests')
class TestCancelUserrequestApi(ConfigDBTestMixin, SetTimeMixin, APITestCase):
    ''' Test canceling user requests via API. Mocking out modify_ipp_time_from_requets
        as it is called on state change, but tested elsewhere '''
    def setUp(self):
        super().setUp()
        self.user = mixer.blend(User)
        self.proposal = mixer.blend(Proposal)
        mixer.blend(Membership, user=self.user, proposal=self.proposal)
        self.client.force_login(self.user)

    def test_cancel_pending_ur(self, modify_mock):
        userrequest = mixer.blend(UserRequest, state='PENDING', proposal=self.proposal)
        requests = mixer.cycle(3).blend(Request, state='PENDING', user_request=userrequest)

        response = self.client.put(reverse('api:user_requests-cancel', kwargs={'pk': userrequest.id}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(UserRequest.objects.get(pk=userrequest.id).state, 'CANCELED')
        for request in requests:
            self.assertEqual(Request.objects.get(pk=request.id).state, 'CANCELED')

    def test_cancel_pending_ur_some_requests_not_pending(self, modify_mock):
        userrequest = mixer.blend(UserRequest, state='PENDING', proposal=self.proposal)
        pending_r = mixer.blend(Request, state='PENDING', user_request=userrequest)
        completed_r = mixer.blend(Request, state='COMPLETED', user_request=userrequest)
        we_r = mixer.blend(Request, state='WINDOW_EXPIRED', user_request=userrequest)
        response = self.client.put(reverse('api:user_requests-cancel', kwargs={'pk': userrequest.id}))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(UserRequest.objects.get(pk=userrequest.id).state, 'CANCELED')
        self.assertEqual(Request.objects.get(pk=pending_r.id).state, 'CANCELED')
        self.assertEqual(Request.objects.get(pk=completed_r.id).state, 'COMPLETED')
        self.assertEqual(Request.objects.get(pk=we_r.id).state, 'WINDOW_EXPIRED')

    def test_cannot_cancel_expired_ur(self, modify_mock):
        userrequest = mixer.blend(UserRequest, state='WINDOW_EXPIRED', proposal=self.proposal)
        expired_r = mixer.blend(Request, state='WINDOW_EXPIRED', user_request=userrequest)
        response = self.client.put(reverse('api:user_requests-cancel', kwargs={'pk': userrequest.id}))

        self.assertEqual(response.status_code, 400)
        self.assertEqual(UserRequest.objects.get(pk=userrequest.id).state, 'WINDOW_EXPIRED')
        self.assertEqual(Request.objects.get(pk=expired_r.id).state, 'WINDOW_EXPIRED')

    def test_cannot_cancel_completed_ur(self, modify_mock):
        userrequest = mixer.blend(UserRequest, state='COMPLETED', proposal=self.proposal)
        completed_r = mixer.blend(Request, state='COMPLETED', user_request=userrequest)
        expired_r = mixer.blend(Request, state='WINDOW_EXPIRED', user_request=userrequest)
        response = self.client.put(reverse('api:user_requests-cancel', kwargs={'pk': userrequest.id}))

        self.assertEqual(response.status_code, 400)
        self.assertEqual(UserRequest.objects.get(pk=userrequest.id).state, 'COMPLETED')
        self.assertEqual(Request.objects.get(pk=expired_r.id).state, 'WINDOW_EXPIRED')
        self.assertEqual(Request.objects.get(pk=completed_r.id).state, 'COMPLETED')


@patch('valhalla.userrequests.state_changes.modify_ipp_time_from_requests')
class TestUpdateRequestStatesAPI(APITestCase):
    def setUp(self):
        self.user = mixer.blend(User, is_staff=True)
        self.proposal = mixer.blend(Proposal)
        mixer.blend(Membership, user=self.user, proposal=self.proposal)
        self.client.force_login(self.user)
        self.ur = mixer.blend(UserRequest, operator='MANY', state='PENDING', proposal=self.proposal)
        self.requests = mixer.cycle(3).blend(Request, user_request=self.ur, state='PENDING')

    @responses.activate
    def test_no_pond_blocks_no_state_changed(self, modify_mock):
        pond_blocks = []
        responses.add(responses.GET, settings.POND_URL + '/pond/pond/blocks/new/',
                      body=json.dumps(pond_blocks, cls=DjangoJSONEncoder), status=200, content_type='application/json')

        response = self.client.get(reverse('api:isDirty'))
        response_json = response.json()

        self.assertFalse(response_json['isDirty'])

    @responses.activate
    def test_pond_blocks_no_state_changed(self, modify_mock):
        now = timezone.now()
        mixer.cycle(3).blend(Window, request=(r for r in self.requests), start=now - timedelta(days=2),
                             end=now + timedelta(days=1))
        molecules1 = basic_mixer.cycle(3).blend(PondMolecule, complete=False, failed=False, request_number=self.requests[0].id,
                                                tracking_number=self.ur.id)
        molecules2 = basic_mixer.cycle(3).blend(PondMolecule, complete=False, failed=False, request_number=self.requests[1].id,
                                                tracking_number=self.ur.id)
        molecules3 = basic_mixer.cycle(3).blend(PondMolecule, complete=False, failed=False, request_number=self.requests[2].id,
                                                tracking_number=self.ur.id)
        pond_blocks = basic_mixer.cycle(3).blend(PondBlock, molecules=(m for m in [molecules1, molecules2, molecules3]),
                                                 start=now + timedelta(minutes=30), end=now + timedelta(minutes=40))
        pond_blocks = [pb._to_dict() for pb in pond_blocks]
        responses.add(responses.GET, settings.POND_URL + '/pond/pond/blocks/new/',
                      body=json.dumps(pond_blocks, cls=DjangoJSONEncoder), status=200, content_type='application/json')

        response = self.client.get(reverse('api:isDirty'))
        response_json = response.json()

        self.assertTrue(response_json['isDirty'])
        for i, req in enumerate(self.requests):
            req.refresh_from_db()
            self.assertEqual(req.state, 'PENDING')
        self.ur.refresh_from_db()
        self.assertEqual(self.ur.state, 'PENDING')

    @responses.activate
    def test_pond_blocks_state_change_completed(self, modify_mock):
        now = timezone.now()
        mixer.cycle(3).blend(Window, request=(r for r in self.requests), start=now - timedelta(days=2),
                             end=now - timedelta(days=1))
        molecules1 = basic_mixer.cycle(3).blend(PondMolecule, complete=True, failed=False, request_number=self.requests[0].id,
                                                tracking_number=self.ur.id)
        molecules2 = basic_mixer.cycle(3).blend(PondMolecule, complete=False, failed=False, request_number=self.requests[1].id,
                                                tracking_number=self.ur.id)
        molecules3 = basic_mixer.cycle(3).blend(PondMolecule, complete=False, failed=False, request_number=self.requests[2].id,
                                                tracking_number=self.ur.id)
        pond_blocks = basic_mixer.cycle(3).blend(PondBlock, molecules=(m for m in [molecules1, molecules2, molecules3]),
                                                 start=now - timedelta(minutes=30), end=now - timedelta(minutes=20))
        pond_blocks = [pb._to_dict() for pb in pond_blocks]
        responses.add(responses.GET, settings.POND_URL + '/pond/pond/blocks/new/',
                      body=json.dumps(pond_blocks, cls=DjangoJSONEncoder), status=200, content_type='application/json')

        response = self.client.get(reverse('api:isDirty'))
        response_json = response.json()

        self.assertTrue(response_json['isDirty'])

        request_states = ['COMPLETED', 'WINDOW_EXPIRED', 'WINDOW_EXPIRED']
        for i, req in enumerate(self.requests):
            req.refresh_from_db()
            self.assertEqual(req.state, request_states[i])
        self.ur.refresh_from_db()
        self.assertEqual(self.ur.state, 'COMPLETED')

    @responses.activate
    def test_bad_data_from_pond(self, modify_mock):
        responses.add(responses.GET, settings.POND_URL + '/pond/pond/blocks/new/',
                      body='Internal Server Error', status=500, content_type='application/json')

        response = self.client.get(reverse('api:isDirty'))

        self.assertEqual(response.status_code, 500)


class TestSchedulableRequestsApi(ConfigDBTestMixin, SetTimeMixin, APITestCase):
    def setUp(self):
        super().setUp()

        self.proposal = mixer.blend(Proposal)
        self.user = mixer.blend(User)
        mixer.blend(Membership, user=self.user, proposal=self.proposal, ipp_value=1.0)
        semester = mixer.blend(
            Semester, id='2016B', start=datetime(2016, 9, 1, tzinfo=timezone.utc),
            end=datetime(2016, 12, 31, tzinfo=timezone.utc)
        )
        self.time_allocation_1m0 = mixer.blend(
            TimeAllocation, proposal=self.proposal, semester=semester,
            telescope_class='1m0', std_allocation=100.0, std_time_used=0.0,
            too_allocation=10, too_time_used=0.0, ipp_limit=10.0,
            ipp_time_available=5.0
        )

        # Add a few requests within the current semester
        self.urs = mixer.cycle(10).blend(UserRequest, proposal=self.proposal, submitter=self.user,
                                    observation_type='NORMAL', operator='MANY', state='PENDING')
        for ur in self.urs:
            reqs = mixer.cycle(5).blend(Request, user_request=ur, state='PENDING')
            for req in reqs:
                mixer.blend(Window, request=req, start=datetime(2016, 10, 1, tzinfo=timezone.utc), end=datetime(2016, 11, 1, tzinfo=timezone.utc))
                mixer.blend(Molecule, request=req, exposure_time=60, exposure_count=10, type='EXPOSE', filter='air',
                            instrument_name='1M0-SCICAM-SBIG', bin_x=1, bin_y=1)
                mixer.blend(Target, request=req, type='SIDEREAL', dec=20, ra=34.4)
                mixer.blend(Location, request=req, telescope_class='1m0')
                mixer.blend(Constraints, request=req, max_airmass=2.0, min_lunar_distance=30.0)

        self.client.force_login(self.user)

    def test_setting_time_range_with_no_requests(self):
        start = datetime(2020, 1, 1, tzinfo=timezone.utc).isoformat()
        end = datetime(2020, 4, 1, tzinfo=timezone.utc).isoformat()
        response = self.client.get(reverse('api:user_requests-schedulable-requests') + '?start=' + start + '&end=' + end)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 0)

    def test_get_all_requests_in_semester(self):
        response = self.client.get(reverse('api:user_requests-schedulable-requests'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 10)
        tracking_numbers = [ur.id for ur in self.urs]
        for ur in response.json():
            self.assertIn(ur['id'], tracking_numbers)
