# -*- coding: utf-8 -*-
# © 2016 Antonio Espinosa - <antonio.espinosa@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp.tests.common import TransactionCase
from openerp.exceptions import Warning as UserError


# One test case per method
class TestMassMailing(TransactionCase):
    def setUp(self):
        super(TestMassMailing, self).setUp()
        self.list = self.env['mail.mass_mailing.list'].create({
            'name': 'Test mail tracking',
        })
        self.contact_a = self.env['mail.mass_mailing.contact'].create({
            'list_id': self.list.id,
            'name': 'Test contact A',
            'email': 'contact_a@example.com',
        })
        self.mailing = self.env['mail.mass_mailing'].create({
            'name': 'Test subject',
            'email_from': 'from@example.com',
            'mailing_model': 'mail.mass_mailing.contact',
            'mailing_domain': "[('list_id', 'in', [%d]), "
                              "('opt_out', '=', False)]" % self.list.id,
            'contact_list_ids': [(6, False, [self.list.id])],
            'body_html': '<p>Test email body</p>',
            'reply_to_mode': 'email',
        })

    def resend_mass_mailing(self, first, second):
        self.mailing.send_mail()
        self.assertEqual(len(self.mailing.statistics_ids), first)
        self.env['mail.mass_mailing.contact'].create({
            'list_id': self.list.id,
            'name': 'Test contact B',
            'email': 'contact_b@example.com',
        })
        self.mailing.send_mail()
        self.assertEqual(len(self.mailing.statistics_ids), second)

    def test_avoid_resend_enable(self):
        self.mailing.avoid_resend = True
        self.resend_mass_mailing(1, 2)
        with self.assertRaises(UserError):
            self.mailing.send_mail()

    def test_avoid_resend_disable(self):
        self.mailing.avoid_resend = False
        self.resend_mass_mailing(1, 3)

    def test_tracking_email_link(self):
        self.mailing.send_mail()
        for stat in self.mailing.statistics_ids:
            if stat.mail_mail_id:
                stat.mail_mail_id.send()
            tracking_email = self.env['mail.tracking.email'].search([
                ('mail_id_int', '=', stat.mail_mail_id_int),
            ])
            self.assertTrue(tracking_email)
            self.assertEqual(
                tracking_email.mass_mailing_id.id, self.mailing.id)
            self.assertEqual(tracking_email.mail_stats_id.id, stat.id)
            self.assertEqual(stat.mail_tracking_id.id, tracking_email.id)
            # And now open the email
            metadata = {
                'ip': '127.0.0.1',
                'user_agent': 'Odoo Test/1.0',
                'os_family': 'linux',
                'ua_family': 'odoo',
            }
            tracking_email.event_create('open', metadata)
            self.assertTrue(stat.opened)
            self.assertEqual(stat.tracking_state, 'opened')

    def test_contact_tracking_emails(self):
        self.mailing.send_mail()
        for stat in self.mailing.statistics_ids:
            if stat.mail_mail_id:
                stat.mail_mail_id.send()
        self.assertEqual(len(self.contact_a.tracking_email_ids), 1)
        self.contact_a.email = 'other_contact_a@example.com'
        self.assertEqual(len(self.contact_a.tracking_email_ids), 0)
        self.contact_a.email = 'contact_a@example.com'
        self.assertEqual(len(self.contact_a.tracking_email_ids), 1)