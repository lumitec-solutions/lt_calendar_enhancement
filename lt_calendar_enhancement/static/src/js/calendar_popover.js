odoo.define('lt_calendar_enhancement.calendarpopupbutton', function (require) {
"use strict";
const core = require("web.core");
const _t = core._t;
var CalendarPopover = require('web.CalendarPopover');

CalendarPopover.include({
    events: _.extend({}, CalendarPopover.prototype.events, {
        'click .detailed_form_view': '_onClickDetailedFormView',
        'click .navigate_to': '_onClickNavigateTo',
    }),

    _onClickDetailedFormView: function (ev) {
          this.do_action({
            type: 'ir.actions.act_window',
            res_model: 'calendar.event',
            res_id: parseInt(this.event.id),
            views: [[false, 'form']],
            target: 'current'
        });
    },
    _onClickNavigateTo: function (ev) {
       window.location.href = _.str.sprintf(_t('https://www.google.com/maps/search/?api=1&query=%s'), this.event.extendedProps.record.location);
    },

    });
});
