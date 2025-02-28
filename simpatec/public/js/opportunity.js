frappe.ui.form.on('Opportunity', {
	
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

	// Added from client script
	refresh(frm) {
		var cur_frm = frm;
		console.log("Add button");
		frm.add_custom_button('Angebotsvorlage', function () { frm.trigger('get_items') }, __("Get Items From"));
		// Set the filter on the task field to show only tasks linked to the project
		frm.set_query('customer_subsidiary', function () {
			if(!is_null(cur_frm.doc.party_name)){
				return {
					filters: [
						['Customer Subsidiary', 'customer', '=', frm.doc.party_name]
					]
				};
			}
		});
	},
	get_items(frm) {
		frm.events.start_dialog(frm);
	},
	
	start_dialog(frm) {
		// The fetch-from fields
		var fields = [
			"item_code",
			//  "item_name",
			"positionsart",
			//  "description",
			"qty",
			"uom",
			"rate"];
		let dialog = new frappe.ui.form.MultiSelectDialog({

			// Read carefully and adjust parameters
			doctype: "Angebotsvorlage", // Doctype we want to pick up
			target: frm,
			setters: {
			},
			date_field: "creation", // "modified", "creation", ...
			get_query() {
				// MultiDialog Listfilter
				return {
					filters: {}
				};
			},
			action(selections) {
				var name = selections[0];
				frappe.db.get_doc("Angebotsvorlage", name) // Again, the Doctype we want to pick up
				.then(doc => {
					// Copy the items from the template and paste them into the frm
					for (var n = 0; n < doc.angebotsvorlage_item.length; n++) {
						var item = doc.angebotsvorlage_item[n];

						// Copy-Paste Operation
						var child = {};
						for (var m = 0; m < fields.length; m++) {
							child[fields[m]] = item[fields[m]];
						}
						frm.add_child("items", child);
						frm.refresh_fields("items"); // Refresh Tabelle
					}
				});
			}
		});
	},
	// Default Probability %
	verkaufschance_a_bis_e: function (frm, dt, dn) {
		switch (frm.doc.verkaufschance_a_bis_e.charAt(0)) {
			case 'A':
				frappe.model.set_value(dt, dn, "probability", 90);
				break;
			case 'B':
				frappe.model.set_value(dt, dn, "probability", 50);
				break;
			case 'C':
				frappe.model.set_value(dt, dn, "probability", 20);
				break;
			case 'D':
				frappe.model.set_value(dt, dn, "probability", 10);
				break;
			case 'E':
				frappe.model.set_value(dt, dn, "probability", 5);
				break;
		}
	}
	// Added from client script end
});

frappe.ui.form.on('Opportunity Item',{
	//
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
	
});