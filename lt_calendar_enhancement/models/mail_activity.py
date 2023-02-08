##############################################################################
# Copyright (c) 2022 lumitec GmbH (https://www.lumitec.solutions)
# All Right Reserved
#
# See LICENSE file for full licensing details.
##############################################################################
from odoo import models, Command
from collections import defaultdict
from odoo.tools import is_html_empty


class MailActivity(models.Model):
    _inherit = 'mail.activity'

    def action_create_calendar_event(self):
        """On scheduling meeting through schedule activity the partner gets added to the representative"""
        self.ensure_one()
        representative_ids = self.ids
        representative_ids.append(self.env.user.partner_id.id)
        action = self.env["ir.actions.actions"]._for_xml_id("calendar.action_calendar_event")
        action['context'] = {
            'default_activity_type_id': self.activity_type_id.id,
            'default_res_id': self.env.context.get('default_res_id'),
            'default_res_model': self.env.context.get('default_res_model'),
            'default_name': self.summary or self.res_name,
            'default_description': self.note if not is_html_empty(self.note) else '',
            'default_activity_ids': [(6, 0, self.ids)],

        }
        partners = self.env.user.partner_id
        if self.res_model == 'res.partner' and self.res_id and self.res_id not in partners.ids:
            action['context'] = {
                'default_representative_ids': [(4, self.res_id), (4, self.env.user.partner_id.id)],
            }

        model = self.env[self.res_model].browse(self.res_id)
        if self.res_model in ['helpdesk.ticket', 'sale.order', 'project.task'] and model.partner_id.id \
                and model.partner_id.id not in partners.ids:
            action['context'] = {
                'default_representative_ids': [(4, model.partner_id.id), (4, self.env.user.partner_id.id)],
            }
        if self.res_model == 'event.event' and model.organizer_id.id and model.organizer_id.id not in partners.ids:
            action['context'] = {
                'default_representative_ids': [(4, model.organizer_id.id), (4, self.env.user.partner_id.id)],
            }
        if self.env.context.get('default_res_model') == 'crm.lead':
            action['context'] = {
                'model_id': self.env['ir.model']._get_id(self.env.context.get('default_res_model')),
                'res_id': self.env.context.get('default_res_id'),
                'model_name': self.env.context.get('default_res_model'),
                'default_representative_ids': [(4, model.partner_id.id), (4, self.env.user.partner_id.id)],
            }
        return action

    def _action_done(self, feedback=False, attachment_ids=None):
        """ Overrided to post feedback to the lognote of the meeting and also to prevent the saving of feedback
        to the description
        """
        # marking as 'done'
        messages = self.env['mail.message']
        next_activities_values = []
        if self.activity_category == "meeting":
            self.calendar_event_id.write({'description': ' '})
        for rec in self.calendar_event_id:
            rec.message_post(body=feedback)

        # Search for all attachments linked to the activities we are about to unlink. This way, we
        # can link them to the message posted and prevent their deletion.
        attachments = self.env['ir.attachment'].search_read([
            ('res_model', '=', self._name),
            ('res_id', 'in', self.ids),
        ], ['id', 'res_id'])

        activity_attachments = defaultdict(list)
        for attachment in attachments:
            activity_id = attachment['res_id']
            activity_attachments[activity_id].append(attachment['id'])

        for activity in self:
            # extract value to generate next activities
            if activity.chaining_type == 'trigger':
                vals = activity.with_context(activity_previous_deadline=activity.date_deadline)._prepare_next_activity_values()
                next_activities_values.append(vals)

            # post message on activity, before deleting it
            record = self.env[activity.res_model].browse(activity.res_id)
            record.message_post_with_view(
                'mail.message_activity_done',
                values={
                    'activity': activity,
                    'feedback': feedback,
                    'display_assignee': activity.user_id != self.env.user
                },
                subtype_id=self.env['ir.model.data']._xmlid_to_res_id('mail.mt_activities'),
                mail_activity_type_id=activity.activity_type_id.id,
                attachment_ids=[Command.link(attachment_id) for attachment_id in
                                attachment_ids] if attachment_ids else [],
            )

            # Moving the attachments in the message
            # TODO: Fix void res_id on attachment when you create an activity with an image
            # directly, see route /web_editor/attachment/add
            activity_message = record.message_ids[0]
            message_attachments = self.env['ir.attachment'].browse(activity_attachments[activity.id])
            if message_attachments:
                message_attachments.write({
                    'res_id': activity_message.id,
                    'res_model': activity_message._name,
                })
                activity_message.attachment_ids = message_attachments
            messages |= activity_message

        next_activities = self.env['mail.activity'].create(next_activities_values)
        self.unlink()  # will unlink activity, dont access `self` after that

        return messages, next_activities
