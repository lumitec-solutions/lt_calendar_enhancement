##############################################################################
# Copyright (c) 2022 lumitec GmbH (https://www.lumitec.solutions)
# All Right Reserved
#
# See LICENSE file for full licensing details.
##############################################################################
from odoo import models, api, fields
from odoo.addons.calendar.models.calendar_event import Meeting


def default_get(self, fields):
    """Override the function inorder to pass the defaults values"""
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


class CalendarEvent(models.Model):
    _inherit = "calendar.event"

    @api.model
    def _default_location(self):
        """This function returns the default location of the meeting"""
        if self._context.get('partner_id'):
            partner = self.env['res.partner'].browse(self._context.get('partner_id'))
            return partner.contact_address_complete
        if self._context.get('default_representative_ids'):
            for rec in self._context.get('default_representative_ids'):
                if rec[1] != self.env.user.partner_id.id:
                    model = self.env['res.partner'].browse(rec[1])
                return model.contact_address_complete
        return self.env.user.partner_id.contact_address_complete

    @api.model
    def _default_representative(self):
        """This function returns the default representative_ids of the meeting"""
        partners = self.env.user.partner_id
        active_id = self._context.get('active_id')
        lead = self.env['crm.lead'].browse(active_id)
        if self._context.get(
                'active_model') == 'res.partner' and active_id and active_id not in partners.ids:
            partners |= self.env['res.partner'].browse(active_id)
        if self._context.get(
                'active_model') == 'crm.lead' and active_id and lead.partner_id.id not in partners.ids:
            partners |= lead.partner_id
        return partners

    @api.model
    def _default_partners(self):
        """This function returns the default partner_ids of the meeting"""
        partners = self.env.user.partner_id
        return partners

    @api.model
    def _default_alarm_ids(self):
        """This function returns the default alarm_ids of the meeting"""
        alarm_days = self.env['calendar.alarm'].search(
            [('alarm_type', '=', 'email'), ('duration', '=', 1),
             ('interval', '=', 'days')], limit=1)
        if not alarm_days:
            alarm_days = self.env['calendar.alarm'].create({
                'name': 'Email - 1 Days',
                'duration': 1,
                'interval': 'days',
                'alarm_type': 'email'})
        alarm_hours = self.env['calendar.alarm'].search(
            [('alarm_type', '=', 'email'), ('duration', '=', 1),
             ('interval', '=', 'hours')], limit=1)
        if not alarm_hours:
            alarm_hours = self.env['calendar.alarm'].create({
                'name': 'Email - 1 Hours',
                'duration': 1,
                'interval': 'hours',
                'alarm_type': 'email'})
        alarm_ids = [(4, alarm_days.id, 0), (4, alarm_hours.id, 0)]
        return alarm_ids


    event_id = fields.Many2one('event.event', string='Event',
                               ondelete='cascade', readonly=True)
    model_id = fields.Many2one('ir.model', string='Model',
                               compute='_compute_model_id', store=True)
    location = fields.Char('Location', tracking=True, help="Location of Event", default=_default_location)

    partner_ids = fields.Many2many(
        'res.partner', 'calendar_event_res_partner_rel',
        string='Attendees', default=_default_partners)
    representative_ids = fields.Many2many('res.partner', 'partner_id',
                                          string='Representative',
                                          default=_default_representative)
    is_private_mail = fields.Boolean("Private", default=True)
    meeting_type_id = fields.Many2one('meeting.type', string="Meeting Type")
    alarm_ids = fields.Many2many(
        'calendar.alarm', 'calendar_alarm_calendar_event_rel',
        string='Reminders', ondelete="restrict", default=_default_alarm_ids)

    @api.depends('event_id', 'start', 'opportunity_id')
    def _compute_model_id(self):
        """Computes the model_id"""
        for rec in self:
            if isinstance(rec.id, int):
                if rec.event_id:
                    rec.model_id = self.env['ir.model'].search(
                        [('model', '=', 'event.event')], limit=1)
                elif rec.opportunity_id:
                    rec.model_id = self.env['ir.model'].search(
                        [('model', '=', 'crm.lead')], limit=1)
                else:
                    rec.model_id = self.env['ir.model'].search(
                        [('model', '=', 'calendar.event')], limit=1)

    def add_representatives(self):
        """This function Change Values from Attendees to Representative"""
        meetings = self.env['calendar.event'].search([])
        for meeting in meetings:
            if not meeting.representative_ids and meeting.partner_ids:
                meeting.representative_ids = meeting.partner_ids
            attendees = []
            for partner in meeting.partner_ids:
                if partner.user_ids:
                    attendees.append(partner.id)
            meeting.partner_ids = [(6, 0, attendees)]
