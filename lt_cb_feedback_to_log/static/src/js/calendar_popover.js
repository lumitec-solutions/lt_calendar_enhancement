odoo.define('lt_cb_feedback_to_log.calendarpopupbutton', function (require) {
"use strict";
    var CalendarPopover = require('web.CalendarPopover');

CalendarPopover.include({
        events: _.extend({}, CalendarPopover.prototype.events, {
            'click .detailed_form_view': '_onClickDetailedFormView',
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

    });
});
