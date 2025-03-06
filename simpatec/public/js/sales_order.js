frappe.ui.form.on('Sales Order', {
    onload(frm){
        // FILTER SALES ORDER WITH RESPECTIVE CONDITIONS
        frm.set_query('sales_order', 'sales_order_clearances', function () {
            return {
                filters: {
                    "eligable_for_clearance": 1,
                    "clear_by": frm.doc.company,
                    "docstatus": 1,
                    "clearance_status": ["!=", "Cleared"]
                },
            };
        });
        
        // FILTER ONLY SELECTED CUSTOMER SOFTWARE MAINTENANCE
        frm.set_query('software_maintenance', function () {
            return {
                filters: {
                    "customer": frm.doc.customer,
                },
            };
        });
    },
    setup: function(frm){
		frm.copy_from_previous_row = function(parentfield, current_row, fieldnames){
			

			var data = frm.doc[parentfield];
			let idx = data.indexOf(current_row);
			if (data.length === 1 || data[0] === current_row) return;
			
			if (typeof fieldnames === "string") {
				fieldnames = [fieldnames];
			}			
			
			$.each(fieldnames, function (i, fieldname) {
				frappe.model.set_value(
					current_row.doctype,
					current_row.name,
					fieldname,
					data[idx - 1][fieldname]
				);
			});
		},
		frm.auto_fill_all_empty_rows = function(doc, dt, dn, table_fieldname, fieldname) {
			var d = locals[dt][dn];
			if(d[fieldname]){
				var cl = doc[table_fieldname] || [];
				for(var i = 0; i < cl.length; i++) {
					if(cl[i][fieldname]) cl[i][fieldname] = d[fieldname];
				}
			}
			refresh_field(table_fieldname);
		},
		frm.occurence_len = function(arr, element){
			
			return arr.filter(
				(ele) => ele.item_language == element
			).length;
		}
	},

    refresh(frm) {

        if(frm.doc.docstatus == 0){
            // Conditional Enable and required Toggle on Software Maintenance
            frm.events.software_maintenance_conditional_toggle_reqd(frm)

            // Add Conditional Mandatory On Start/End Dates
            frm.events.start_end_date_conditional_mandatory(frm)
        }

        // GET SIMPATEC GLOBAL SETTINGS
        frm.events.get_simpatec_settings(frm)

        $('[data-doctype="Software Maintenance"]').find("button").hide();
        if (['First Sale', 'RTO', 'Subscription Annual'].includes(frm.doc.sales_order_type) && frm.doc.docstatus == 1 && !frm.doc.software_maintenance) {
            frm.add_custom_button('Software Maintenance', function () { 
                frappe.model.open_mapped_doc({
                    method: "simpatec.events.sales_order.make_software_maintenance",
        			frm: frm
        		})                
            }, __("Create"));
        }

        // MAKE TABLE FULL WIDTH
        if(frm.doc.sales_order_type == "Internal Clearance"){
            $("div[data-fieldname='sales_order_clearances']").parents(".form-column").addClass("col-md-12")
        }else {
            $("div[data-fieldname='sales_order_clearances']").parents(".form-column").removeClass("col-md-12")
        }

        frm.set_query('customer_subsidiary', function () {
            if (!is_null(cur_frm.doc.customer)) {
                return {
                    filters: [
                        ['Customer Subsidiary', 'customer', '=', frm.doc.customer]
                    ]
                };
            }
        });
    },

    internal_clearance_details: function(frm){
        frappe.call({
            method: "simpatec.events.sales_order.update_clearance_and_margin_amount",
            args: {
                self: frm.doc
            },
            async: false,
            callback: function(r){
                if(r.message){
                    r = r.message
                    frm.set_value("po_total", r.po_total)
                    frm.set_value("so_margin", r.so_margin)
                    frm.set_value("so_margin_percent", r.so_margin_percent)
                    frm.set_value("clearance_amount", r.clearance_amount)
                }
            }
        })
        
    },


    get_simpatec_settings(frm){ // SIMPATECH GLOBAL SETTING FUNCTION
        frm.doc.clearance_item = ""
        frm.call({
            method: "frappe.client.get",
            args: {
                fieldname: "clearance_item",
                doctype: "SimpaTec Settings"
            },
            async: false,
            callback: function (r) {
                if (r.message) {
                    frm.doc.clearance_item = r.message.clearance_item; // SET CLEARANCE ITEM IN GLOBAL FRM VARIABLE.
                }
            }
        });
    },
    eligable_for_clearance(frm){ // ELIGIBLE FOR CLEARANCE CHECK FUNCTIONALITY
        // SET CLEAR BY REQUIRED IF ELIGABLE FOR CLEARANCE IS CHECKED
        if (frm.doc.eligable_for_clearance){
            frm.toggle_reqd("clear_by", 1)
        }else{
            frm.toggle_reqd("clear_by", 0)
        }
    },
    sales_order_type(frm){
        // MAKE TABLE FULL WIDTH
        if(frm.doc.sales_order_type == "Internal Clearance"){
            $("div[data-fieldname='sales_order_clearances']").parents(".form-column").addClass("col-md-12")
        }else{
            $("div[data-fieldname='sales_order_clearances']").parents(".form-column").removeClass("col-md-12")
        }

        // Conditional Enable and required Toggle on Software Maintenance
        frm.events.software_maintenance_conditional_toggle_reqd(frm)
        
        // Add Conditional Mandatory On Start/End Dates
        frm.events.start_end_date_conditional_mandatory(frm)
    },

    software_maintenance_conditional_toggle_reqd(frm){
        if (frm.doc.sales_order_type == "First Sale") {
            frm.toggle_enable("software_maintenance", 0)
            frm.toggle_reqd("software_maintenance", 0)
        }
        else if (["Follow-Up Sale", "Reoccuring Maintenance"].includes(frm.doc.sales_order_type)) {
            frm.toggle_reqd("software_maintenance", 1)
            frm.toggle_enable("software_maintenance", 1)
        }
        else {
            frm.toggle_reqd("software_maintenance", 0)
            frm.toggle_enable("software_maintenance", 1)
        }
    },

    start_end_date_conditional_mandatory: function(frm){
        if (["First Sale", "Follow-Up Sale", "Reoccuring Maintenance", "RTO", "Subscription Annual"].includes(frm.doc.sales_order_type)) {
            frm.toggle_reqd("performance_period_start", 1)
            frm.toggle_reqd("performance_period_end", 1)
        }
        else {
            frm.toggle_reqd("performance_period_start", 0)
            frm.toggle_reqd("performance_period_end", 0)
        }
    },  
    
    performance_period_start: function (frm) {
        var currentDate = moment(frm.doc.performance_period_start);
        var futureMonth = moment(currentDate).add(364, 'd');
        frm.set_value("performance_period_end", futureMonth.format('YYYY-MM-DD'))
        if (["First Sale", "Follow-Up Sale", "Reoccurring Maintenance"].includes(frm.doc.sales_order_type)){
            $.each(frm.doc.items || [], function (i, d) {
                if (!d.start_date){
                    d.start_date = frm.doc.performance_period_start;
                } else if (d.start_date != frm.doc.performance_period_start){
                    d.start_date = frm.doc.performance_period_start;
                }
            });
            refresh_field("items");
        }
    },
    performance_period_end: function (frm) {
        $.each(frm.doc.items || [], function (i, d) {
            if (!d.end_date){
                d.end_date = frm.doc.performance_period_end;
            }
            else if (d.end_date != frm.doc.performance_period_end){
                d.end_date = frm.doc.performance_period_end
            }
            
        });
        refresh_field("items");
    },

})

// SALES ORDER CLEARANCE TABLE EVENTS
frappe.ui.form.on("Sales Order Clearances", {
    sales_order_clearances_add(frm, cdt, cdn){ // EVENT TRIGGER ON ADD ROW
        var cur_row = locals[cdt][cdn];
        if(!is_null(frm.doc.customer)){ // CHECK IF CUSTOMER IS EMPTY

            // CHECK THE SAME ROW INDEX OF ITEM TABLE, IF ROW IS NOT AVAILABLE 
            // THEN ADD NEW ROW IN ITEM TABLE, OTHERWISE UPDATE THE EXISTING INDEX ROW
            var item_row = frm.doc.items[cur_row.idx - 1];  // GET THE ITEM TABLE SAME ROW INDEX
            if (!is_null(item_row)) {
                // UPDATING SAME ROW INDEX IN ITEM TABLE
                frappe.model.set_value(item_row.doctype, item_row.name, "item_code", frm.doc.clearance_item)
            }else{
                // CREATE NEW ROW IN ITEM TABLE
                var row = frappe.model.add_child(frm.doc, "Sales Order Item", "items");
                frappe.model.set_value(row.doctype, row.name, "item_code", frm.doc.clearance_item)
            } 
            refresh_field("items");
            
        }
        else{
            // IF CUSTOMER NOT AVAILABLE THEN THROW WARNING MESSAGE
            frm.doc.sales_order_clearances = [];
            refresh_field("sales_order_clearances");
            frappe.msgprint("Please specify: Customer. It is needed to fetch Sales Order Details.")
        }
    },
    sales_order(frm, cdt, cdn){ // EVENT TRIGGER ON SALES ORDER FIELD
        var cur_row = locals[cdt][cdn];
        var item_row = frm.doc.items[cur_row.idx - 1];
        // CHECK IF ITEM ROW IS ALREADY AVAILABLE
        if (!is_null(item_row)){
            var formatted_currency = frappe.format(cur_row.net_total, { fieldtype: "Currency", currency: frm.doc.currency });
            frappe.model.set_value(item_row.doctype, item_row.name, "start_date", cur_row.date)
            // let row_description = `${cur_row.customer_name} - ${cur_row.quotation_label} - ${cur_row.sales_order} - ${cur_row.clearance_details} - ${$(formatted_currency).text()} <br>Period Start Date: ${cur_row.start_date} - Period End Date: ${cur_row.end_date} `
            let row_description = ``
            if (!is_null(cur_row.customer_name)){
                row_description += ` ${cur_row.customer_name} -`
            }
            if (!is_null(cur_row.quotation_label)) {
                row_description += ` ${cur_row.quotation_label} -`
            }
            if (!is_null(cur_row.sales_order)) {
                row_description += ` ${cur_row.sales_order} -`
            }
            if (!is_null(cur_row.clearance_details)) {
                row_description += ` ${cur_row.clearance_details} -`
            }
            if (!is_null(formatted_currency)) {
                row_description += ` ${$(formatted_currency).text()} -`
            }
            row_description = trim_string(row_description, "-")
            row_description += ` <br>`
            if (!is_null(cur_row.start_date)) {
                row_description += `Period Start Date: ${ frappe.format(cur_row.start_date, { fieldtype: "Date"}) } - `
            }
            if (!is_null(cur_row.end_date)) {
                row_description += `Period End Date: ${ frappe.format(cur_row.end_date, { fieldtype: "Date" }) }`
            }
            // row_description = trim_string(row_description, "-")

            frappe.model.set_value(item_row.doctype, item_row.name, "description", row_description)
            frappe.model.set_value(item_row.doctype, item_row.name, "item_description_en", row_description)
            frappe.model.set_value(item_row.doctype, item_row.name, "item_description_de", row_description)
            frappe.model.set_value(item_row.doctype, item_row.name, "item_description_fr", row_description)
            frappe.model.set_value(item_row.doctype, item_row.name, "rate", cur_row.clearance_amount)
        }
        refresh_field("items");
    },

})


function trim_string(string, character){
    let trim_idx = string.lastIndexOf(character);
    string = string.substring(0, trim_idx)
    return string
}


frappe.ui.form.on('Sales Order Item',{
    item_code: function (frm, cdt, cdn) {
        if (["First Sale", "Follow-Up Sale", "Reoccuring Maintenance"].includes(frm.doc.sales_order_type)){
            var row = locals[cdt][cdn];
            if (frm.doc.performance_period_start) {
                row.start_date = frm.doc.performance_period_start;
                refresh_field("start_date", cdn, "items");
            }
            if (frm.doc.performance_period_end) {
                row.end_date = frm.doc.performance_period_end;
                refresh_field("end_date", cdn, "items");
            }
        }

    },
    item_name: function(frm, cdt, cdn){

		var data = frm.doc.items;
		var row = locals[cdt][cdn];
		if (data.length === 1 || data[0] === row) {
			if (frm.doc.language){
				row.item_language = frm.doc.language;
				refresh_field("item_language", cdn, "items");
			}
			
		} else {
			frm.copy_from_previous_row("items", row, ["item_language"]);
		}	
	},

	item_language: function(frm, cdt, cdn){
		
		var data = frm.doc.items;
		
		var row = locals[cdt][cdn];
		if(!(frm.doc.language=== row.item_language)){			
			let row_occurence = frm.occurence_len(data, row.item_language);
			if (row_occurence < data.length && !cur_dialog){
			
				frappe.confirm("💬"+__("  The language <b>{0}</b> in the just edited row is different to the others. Should <b>{0}</b> apply to all rows?", [ row.item_language]),
				()=>{
					frm.auto_fill_all_empty_rows(frm.doc, cdt, cdn, "items", "item_language");
				}, ()=>{
					//cancel
				})
			}
			//
		}
		else if (frm.doc.language=== row.item_language){
			
			let row_occurence = frm.occurence_len(data, row.item_language);
			if (row_occurence < data.length && !cur_dialog){
				//				
				frappe.confirm("💬"+__("    The language <b>'{0}'</b> in the just edited row is different to the others. Should <b>'{0}'</b> apply to all rows?", [ row.item_language]),
					()=>{
							frm.auto_fill_all_empty_rows(frm.doc, cdt, cdn, "items", "item_language");
						}, 
					()=>{
						//cancel
					}
				)
			}
		}
		
		
	},
})
