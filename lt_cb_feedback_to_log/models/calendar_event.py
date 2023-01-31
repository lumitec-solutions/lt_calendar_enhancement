##############################################################################
# Copyright (c) 2022 lumitec GmbH (https://www.lumitec.solutions)
# All Right Reserved
#
# See LICENSE file for full licensing details.
##############################################################################
from odoo import models, api, _, fields


class CalendarEvent(models.Model):
    _inherit = "calendar.event"

    @api.model
    def _default_location(self):
        if self._context.get('partner_id'):
            partner = self.env['res.partner'].browse(self._context.get('partner_id'))
            print(partner.read(), 'contact contact_address_complete')
            return partner.contact_address_complete
        if self._context.get('default_representative_ids'):
            for rec in self._context.get('default_representative_ids'):
                if rec[1] != self.env.user.partner_id.id:
                    model = self.env['res.partner'].browse(rec[1])
                return model.contact_address_complete

    location = fields.Char('Location', tracking=True, help="Location of Event", default=_default_location)
