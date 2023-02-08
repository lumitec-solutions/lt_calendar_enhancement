##############################################################################
# Copyright (c) 2022 lumitec GmbH (https://www.lumitec.solutions)
# All Right Reserved
#
# See LICENSE file for full licensing details.
##############################################################################
from odoo import models, fields


class ProfileConfiguration(models.Model):
    _name = 'meeting.type'
    _description = 'Meeting type'

    name = fields.Char("Name",
                       help="Name of the meeting type or category of meeting")
