##############################################################################
# Copyright (c) 2022 lumitec GmbH (https://www.lumitec.solutions)
# All Right Reserved
#
# See LICENSE file for full licensing details.
##############################################################################
from odoo import models, api, _, fields
from odoo.addons.calendar.models.calendar_event import Meeting


class CalendarEvent(models.Model):
    _inherit = "calendar.event"

    def default_get(self, fields):
        # super default_model='crm.lead' for easier use in addons
        if self.env.context.get('default_res_model') and not self.env.context.get('default_res_model_id'):
            self = self.with_context(
                default_res_model_id=self.env['ir.model']._get_id(self.env.context['default_res_model'])
            )
        defaults = super(Meeting, self).default_get(fields)
        # support active_model / active_id as replacement of default_* if not already given
        if 'res_model_id' not in defaults and 'res_model_id' in fields and \
                self.env.context.get('active_model') and self.env.context['active_model'] != 'calendar.event':
            defaults['res_model_id'] = self.env['ir.model']._get_id(self.env.context['active_model'])
            defaults['res_model'] = self.env.context.get('active_model')
        if 'res_id' not in defaults and 'res_id' in fields and \
                defaults.get('res_model_id') and self.env.context.get('active_id'):
            defaults['res_id'] = self.env.context['active_id']
        if self._context.get('model_name') == 'crm.lead':
            defaults['res_model_id'] = self._context.get('model_id')
            defaults['res_id'] = self._context.get('res_id')
        return defaults

    Meeting.default_get = default_get

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
