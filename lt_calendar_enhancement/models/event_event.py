from odoo import models, api, _, fields


class Event(models.Model):
    _inherit = "event.event"

    is_meeting = fields.Boolean('Is a meeting')

    def create_meetings(self):
        """This function is used to create meetings"""
        events = self.env['event.event'].search([('is_meeting', '=', False)])
        for rec in events:
            attendees = []
            if rec.user_id and rec.user_id.partner_id:
                attendees.append(rec.user_id.partner_id.id)
            if rec.main_representative_id and rec.main_representative_id.partner_id:
                attendees.append(rec.main_representative_id.partner_id.id)
            for rep in rec.representative_ids:
                if rep.partner_id:
                    attendees.append(rep.partner_id.id)
            meeting_name = _("Event - %s") % (rec.name)
            calendar_event_vals = {'name': meeting_name,
                                   'start': rec.date_begin,
                                   'stop': rec.date_end,
                                   'allday': False,
                                   'location': rec.address_id.name if rec.address_id else False,
                                   'partner_ids': [(6, 0, attendees)],
                                   'event_id': rec.id, }
            meeting = self.env['calendar.event'].create(calendar_event_vals)
            rec.is_meeting = True

    @api.model
    def create(self, vals):
        res = super(Event, self).create(vals)
        attendees = []
        if res.user_id and res.user_id.partner_id:
            attendees.append(res.user_id.partner_id.id)
        if res.main_representative_id and res.main_representative_id.partner_id:
            attendees.append(res.main_representative_id.partner_id.id)
        for rep in res.representative_ids:
            if rep.partner_id:
                attendees.append(rep.partner_id.id)
        meeting_name = _("Event - %s") % (res.name)
        calendar_event_vals = {'name': meeting_name,
                               'start': res.date_begin,
                               'stop': res.date_end,
                               'allday': False,
                               'location': res.address_id.name if res.address_id else False,
                               'partner_ids': [(6, 0, attendees)],
                               'event_id': res.id, }
        self.env['calendar.event'].create(calendar_event_vals)
        res.is_meeting = True
        return res

    def write(self, vals):
        calendar_event_vals = {}
        if vals.get('name'):
            meeting_name = _("Event - %s") % (vals.get('name'))
            calendar_event_vals['name'] = meeting_name
        if vals.get('date_begin'):
            calendar_event_vals['start'] = vals.get('date_begin')
        if vals.get('date_end'):
            calendar_event_vals['stop'] = vals.get('date_end')
        if vals.get('address_id'):
            location_id = self.env['res.partner'].browse(vals.get('address_id'))
            calendar_event_vals['location'] = location_id.name
        res = super(Event, self).write(vals)
        attendees = []
        if self.user_id and self.user_id.partner_id:
            attendees.append(self.user_id.partner_id.id)
        if self.main_representative_id and self.main_representative_id.partner_id:
            attendees.append(self.main_representative_id.partner_id.id)
        for rep in self.representative_ids:
            if rep.partner_id:
                attendees.append(rep.partner_id.id)
        calendar_event_vals['partner_ids'] = [(6, 0, attendees)]
        if calendar_event_vals:
            calendar_event_ids = self.env['calendar.event'].search(
                [('event_id', 'in', self.ids)])
            calendar_event_ids.write(calendar_event_vals)
        return res
