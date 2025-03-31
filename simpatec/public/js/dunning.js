frappe.ui.form.on('Dunning', {
    refresh(frm) {
        // Set the filter on the task field to show only tasks linked to the project
        frm.set_query('customer_subsidiary', function () {
            if (!is_null(cur_frm.doc.customer)) {
                return {
                    filters: [
                        ['Customer Subsidiary', 'customer', '=', frm.doc.customer]
                    ]
                };
            }
        });
    }
})