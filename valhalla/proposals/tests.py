from django.test import TestCase
from django.core import mail
from django.contrib.auth.models import User
from django.db.utils import IntegrityError
from django.conf import settings
from django.utils import timezone
from mixer.backend.django import mixer
from unittest.mock import patch
from requests import HTTPError
import responses
import datetime

from valhalla.proposals.models import ProposalInvite, Proposal, Membership, ProposalNotification, TimeAllocation, Semester
from valhalla.userrequests.models import UserRequest
from valhalla.accounts.models import Profile
from valhalla.proposals.accounting import split_time, get_time_totals_from_pond, query_pond
from valhalla.proposals.tasks import run_accounting, update_time_allocation

class TestProposal(TestCase):
    def test_add_users(self):
        proposal = mixer.blend(Proposal)
        user = mixer.blend(User, email='email1@lcogt.net')
        emails = ['email1@lcogt.net', 'notexist@lcogt.net']
        proposal.add_users(emails, Membership.CI)
        self.assertIn(proposal, user.proposal_set.all())
        self.assertTrue(ProposalInvite.objects.filter(email='notexist@lcogt.net').exists())

    def test_no_dual_membership(self):
        proposal = mixer.blend(Proposal)
        user = mixer.blend(User)
        Membership.objects.create(user=user, proposal=proposal, role=Membership.PI)
        with self.assertRaises(IntegrityError):
            Membership.objects.create(user=user, proposal=proposal, role=Membership.CI)


class TestProposalInvitation(TestCase):
    def test_send_invitation(self):
        invitation = mixer.blend(ProposalInvite)
        invitation.send_invitation()
        self.assertIn(invitation.proposal.id, str(mail.outbox[0].message()))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [invitation.email])

    def test_accept(self):
        invitation = mixer.blend(ProposalInvite)
        user = mixer.blend(User)
        invitation.accept(user)
        self.assertIn(invitation.proposal, user.proposal_set.all())


class TestProposalNotifications(TestCase):
    def setUp(self):
        self.proposal = mixer.blend(Proposal)
        self.user = mixer.blend(User)
        mixer.blend(Membership, user=self.user, proposal=self.proposal)
        self.userrequest = mixer.blend(UserRequest, proposal=self.proposal, state='PENDING')

    def test_all_proposal_notification(self):
        mixer.blend(Profile, user=self.user, notifications_enabled=True)
        self.userrequest.state = 'COMPLETED'
        self.userrequest.save()
        self.assertIn(self.userrequest.group_id, str(mail.outbox[0].message()))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.user.email])

    def test_single_proposal_notification(self):
        mixer.blend(Profile, user=self.user, notifications_enabled=False)
        mixer.blend(ProposalNotification, user=self.user, proposal=self.proposal)
        self.userrequest.state = 'COMPLETED'
        self.userrequest.save()
        self.assertIn(self.userrequest.group_id, str(mail.outbox[0].message()))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.user.email])

    def test_user_loves_notifications(self):
        mixer.blend(Profile, user=self.user, notifications_enabled=True)
        mixer.blend(ProposalNotification, user=self.user, proposal=self.proposal)
        self.userrequest.state = 'COMPLETED'
        self.userrequest.save()
        self.assertIn(self.userrequest.group_id, str(mail.outbox[0].message()))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.user.email])

    def test_no_notifications(self):
        self.userrequest.state = 'COMPLETED'
        self.userrequest.save()
        self.assertEqual(len(mail.outbox), 0)


class TestAccounting(TestCase):
    def test_split_time(self):
        start = datetime.datetime(2017, 1, 1)
        end = datetime.datetime(2017, 1, 5)
        chunks = split_time(start, end, chunks=4)
        self.assertEqual(len(chunks), 4)
        self.assertEqual(chunks[0][0], start)
        self.assertEqual(chunks[3][1], end)

    @patch('valhalla.proposals.accounting.query_pond', return_value=1)
    def test_time_totals_from_pond(self, qp_mock):
        ta = mixer.blend(TimeAllocation)
        result = get_time_totals_from_pond(ta, ta.semester.start, ta.semester.end, False)
        self.assertEqual(result, 1)
        self.assertEqual(qp_mock.call_count, 1)

    @patch('valhalla.proposals.accounting.query_pond', side_effect=HTTPError)
    def test_time_totals_from_pond_timeout(self, qa_mock):
        ta = mixer.blend(TimeAllocation)
        with self.assertRaises(RecursionError):
            get_time_totals_from_pond(ta, ta.semester.start, ta.semester.end, False)

        self.assertEqual(qa_mock.call_count, 4)

    @responses.activate
    def test_query_pond(self):
        responses.add(
            responses.GET,
            '{}/pond/pond/accounting/summary'.format(settings.POND_URL),
            body='{ "block_bounded_attempted_hours": 1, "attempted_hours": 2 }',
            content_type='application/json'
        )
        self.assertEqual(query_pond(None, datetime.datetime(2017, 1, 1), datetime.datetime(2017, 2, 1), None, False), 2)
        self.assertEqual(query_pond(None, datetime.datetime(2017, 1, 1), datetime.datetime(2017, 2, 1), None, True), 1)

    @patch('valhalla.proposals.accounting.query_pond', return_value=1)
    def test_run_accounting(self, qa_mock):
        semester = mixer.blend(
            Semester, start=datetime.datetime(2017, 1, 1, tzinfo=timezone.utc), end=datetime.datetime(2017, 4, 30, tzinfo=timezone.utc))
        talloc = mixer.blend(
            TimeAllocation, semester=semester, std_allocation=10, too_allocation=10, std_time_used=0, too_time_used=0
        )
        run_accounting([semester])
        talloc.refresh_from_db()
        self.assertEqual(talloc.std_time_used, 1)
        self.assertEqual(talloc.too_time_used, 1)
