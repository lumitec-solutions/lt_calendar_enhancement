##############################################################################
# Copyright (c) 2022 lumitec GmbH (https://www.lumitec.solutions)
# All Right Reserved
#
# See LICENSE file for full licensing details.
##############################################################################
from odoo.addons.calendar.models.calendar_event import Meeting
from odoo.addons.calendar.models.calendar_alarm_manager import AlarmManager

from odoo import api, fields



def post_load():
    @api.model_create_multi
    def create(self, vals_list):
        vals_list = [
            # Else bug with quick_create when we are filter on an other user
            dict(vals,
                 user_id=self.env.user.id) if not 'user_id' in vals else vals
            for vals in vals_list
        ]

        defaults = self.default_get(
            ['activity_ids', 'res_model_id', 'res_id', 'user_id', 'res_model',
             'partner_ids'])
        meeting_activity_type = self.env['mail.activity.type'].search(
            [('category', '=', 'meeting')], limit=1)
        # get list of models ids and filter out None values directly
        model_ids = list(filter(None, {
            values.get('res_model_id', defaults.get('res_model_id')) for values
            in vals_list}))
        model_name = defaults.get('res_model')
        valid_activity_model_ids = model_name and self.env[
            model_name].sudo().browse(model_ids).filtered(
            lambda m: 'activity_ids' in m).ids or []
        if meeting_activity_type and not defaults.get('activity_ids'):
            for values in vals_list:
                # created from calendar: try to create an activity on the related record
                if values.get('activity_ids'):
                    continue
                res_model_id = values.get('res_model_id',
                                          defaults.get('res_model_id'))
                res_id = values.get('res_id', defaults.get('res_id'))
                user_id = values.get('user_id', defaults.get('user_id'))
                if not res_model_id or not res_id:
                    continue
                if res_model_id not in valid_activity_model_ids:
                    continue
                activity_vals = {
                    'res_model_id': res_model_id,
                    'res_id': res_id,
                    'activity_type_id': meeting_activity_type.id,
                }
                if user_id:
                    activity_vals['user_id'] = user_id
                values['activity_ids'] = [(0, 0, activity_vals)]

        # Add commands to create attendees from partners (if present) if no attendee command
        # is already given (coming from Google event for example).
        # Automatically add the current partner when creating an event if there is none (happens when we quickcreate an event)
        default_partners_ids = defaults.get('partner_ids') or (
        [(4, self.env.user.partner_id.id)])
        vals_list = [
            dict(vals, attendee_ids=self._attendees_values(
                vals.get('partner_ids', default_partners_ids)))
            if not vals.get('attendee_ids')
            else vals
            for vals in vals_list
        ]
        recurrence_fields = self._get_recurrent_fields()
        recurring_vals = [vals for vals in vals_list if vals.get('recurrency')]
        other_vals = [vals for vals in vals_list if not vals.get('recurrency')]
        events = super(Meeting, self).create(other_vals)
        for vals in recurring_vals:
            vals['follow_recurrence'] = True
        recurring_events = super(Meeting, self).create(recurring_vals)
        events += recurring_events

        for event, vals in zip(recurring_events, recurring_vals):
            recurrence_values = {field: vals.pop(field) for field in
                                 recurrence_fields if field in vals}
            if vals.get('recurrency'):
                detached_events = event._apply_recurrence_values(
                    recurrence_values)
                detached_events.active = False

        events.filtered(lambda
                            event: event.start > fields.Datetime.now() and not event.is_private_mail).attendee_ids._send_mail_to_attendees(
            self.env.ref('calendar.calendar_template_meeting_invitation',
                         raise_if_not_found=False)
        )
        events._sync_activities(
            fields={f for vals in vals_list for f in vals.keys()})
        if not self.env.context.get('dont_notify'):
            events._setup_alarms()
        return events

    Meeting.create = create


    def write(self, values):
        detached_events = self.env['calendar.event']
        recurrence_update_setting = values.pop('recurrence_update', None)
        update_recurrence = recurrence_update_setting in ('all_events', 'future_events') and len(self) == 1
        break_recurrence = values.get('recurrency') is False

        update_alarms = False
        update_time = False
        if 'partner_ids' in values:
            values['attendee_ids'] = self._attendees_values(values['partner_ids'])
            update_alarms = True

        time_fields = self.env['calendar.event']._get_time_fields()
        if any([values.get(key) for key in time_fields]) or 'alarm_ids' in values:
            update_alarms = True
            update_time = True

        if (not recurrence_update_setting or recurrence_update_setting == 'self_only' and len(self) == 1) and 'follow_recurrence' not in values:
            if any({field: values.get(field) for field in time_fields if field in values}):
                values['follow_recurrence'] = False

        previous_attendees = self.attendee_ids

        recurrence_values = {field: values.pop(field) for field in self._get_recurrent_fields() if field in values}
        if update_recurrence:
            if break_recurrence:
                # Update this event
                detached_events |= self._break_recurrence(future=recurrence_update_setting == 'future_events')
            else:
                future_update_start = self.start if recurrence_update_setting == 'future_events' else None
                time_values = {field: values.pop(field) for field in time_fields if field in values}
                if recurrence_update_setting == 'all_events':
                    # Update all events: we create a new reccurrence and dismiss the existing events
                    self._rewrite_recurrence(values, time_values, recurrence_values)
                else:
                    # Update future events
                    detached_events |= self._split_recurrence(time_values)
                    self.recurrence_id._write_events(values, dtstart=future_update_start)
        else:
            super(Meeting, self).write(values)
            self._sync_activities(fields=values.keys())

        # We reapply recurrence for future events and when we add a rrule and 'recurrency' == True on the event
        if recurrence_update_setting not in ['self_only', 'all_events'] and not break_recurrence:
            detached_events |= self._apply_recurrence_values(recurrence_values, future=recurrence_update_setting == 'future_events')

        (detached_events & self).active = False
        (detached_events - self).with_context(archive_on_error=True).unlink()

        # Notify attendees if there is an alarm on the modified event, or if there was an alarm
        # that has just been removed, as it might have changed their next event notification
        if not self.env.context.get('dont_notify') and update_alarms:
            self._setup_alarms()
        attendee_update_events = self.filtered(lambda ev: ev.user_id != self.env.user)
        if update_time and attendee_update_events:
            # Another user update the event time fields. It should not be auto accepted for the organizer.
            # This prevent weird behavior when a user modified future events time fields and
            # the base event of a recurrence is accepted by the organizer but not the following events
            attendee_update_events.attendee_ids.filtered(lambda att: self.user_id.partner_id == att.partner_id).write({'state': 'needsAction'})

        current_attendees = self.filtered('active').attendee_ids
        if 'partner_ids' in values:
            # we send to all partners and not only the new ones
            if not self.is_private_mail:
                (current_attendees - previous_attendees)._send_mail_to_attendees(
                    self.env.ref('calendar.calendar_template_meeting_invitation', raise_if_not_found=False)
                )
        if 'start' in values:
            start_date = fields.Datetime.to_datetime(values.get('start'))
            # Only notify on future events
            if start_date and start_date >= fields.Datetime.now():
                if not self.is_private_mail:
                    (current_attendees & previous_attendees).with_context(
                        calendar_template_ignore_recurrence=not update_recurrence
                    )._send_mail_to_attendees(
                        self.env.ref('calendar.calendar_template_meeting_changedate', raise_if_not_found=False)
                    )

        return True

    Meeting.write = write

    @api.model
    def _send_reminder(self):
        # Executed via cron
        events_by_alarm = self._get_events_by_alarm_to_notify('email')
        if not events_by_alarm:
            return

        event_ids = list(set(
            event_id for event_ids in events_by_alarm.values() for event_id in
            event_ids))
        events = self.env['calendar.event'].browse(event_ids)
        attendees = events.attendee_ids.filtered(
            lambda a: a.state != 'declined')
        alarms = self.env['calendar.alarm'].browse(events_by_alarm.keys())
        for alarm in alarms:
            alarm_attendees = attendees.filtered(
                lambda attendee: attendee.event_id.id in events_by_alarm[
                    alarm.id] and not attendee.event_id.is_private_mail)
            alarm_attendees.with_context(
                mail_notify_force_send=True,
                calendar_template_ignore_recurrence=True
            )._send_mail_to_attendees(
                alarm.mail_template_id,
                force_send=True
            )

    AlarmManager._send_reminder = _send_reminder
