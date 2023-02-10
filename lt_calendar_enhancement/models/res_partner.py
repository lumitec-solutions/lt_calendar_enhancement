##############################################################################
# Copyright (c) 2022 lumitec GmbH (https://www.lumitec.solutions)
# All Right Reserved
#
# See LICENSE file for full licensing details.
##############################################################################
from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _compute_meeting_count(self):
        """Computes the meeting count"""
        super()._compute_meeting_count()
        for rec in self:
            count = self.env['calendar.event'].search_count([('representative_ids', 'in',
                                                              rec.ids)])
            rec.meeting_count += count

    def schedule_meeting(self):
        self.ensure_one()
        representative_ids = self.ids
        representative_ids.append(self.env.user.partner_id.id)
        action = self.env["ir.actions.actions"]._for_xml_id("calendar.action_calendar_event")
        action['context'] = {
            'default_representative_ids': representative_ids,
        }
        action['domain'] = ['|', ('id', 'in', self._compute_meeting()[self.id]), ('representative_ids', 'in', self.ids)]
        return action
