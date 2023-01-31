##############################################################################
# Copyright (c) 2022 lumitec GmbH (https://www.lumitec.solutions)
# All Right Reserved
#
# See LICENSE file for full licensing details.
##############################################################################
{
    'name': 'Calendar Enhancement',
    'summary': 'Meeting Feedback and Quick Jump into the Detail View,'
               'Add Client Adress to Calendar as prefilled',
    'author': "lumitec GmbH",
    'website': "https://www.lumitec.solutions",
    'category': '',
    'version': '15.0.1.0.0',
    'license': 'OPL-1',
    'depends': [
        'base',
        'web',
        'calendar'
    ],
    'data': [
    ],
    'assets': {
        'web.assets_qweb': [
            'lt_calendar_enhancement/static/src/xml/web_calendar.xml',
        ],
        'web.assets_backend': [
            'lt_calendar_enhancement/static/src/js/calendar_popover.js',

        ],
    },

    'installable': True,
    'application': False,
    'auto_install': False,
}
