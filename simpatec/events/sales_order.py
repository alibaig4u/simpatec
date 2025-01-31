import json
import frappe
from frappe import _
from frappe.utils import cint, cstr, flt, add_days, add_years, today, getdate
from frappe.model.mapper import get_mapped_doc
from datetime import date, timedelta, datetime
from dateutil.relativedelta import relativedelta


@frappe.whitelist()
def validate(doc, handler=None):
	if doc.sales_order_type == "Internal Clearance":
		doc.eligable_for_clearance = 0
		doc.internal_clearance_details = ""
	elif doc.eligable_for_clearance:
		doc.sales_order_clearances = []

	if doc.software_maintenance:
		if doc.sales_order_type == "First Sale" and frappe.db.exists("Sales Order", {"sales_order_type": "First Sale", "software_maintenance": doc.software_maintenance}):
			frappe.throw("First Sales for {0} Exist<br>Select Follow-up Sales or Follow-up Maintenance".format(frappe.get_desk_link("Software Maintenance", doc.software_maintenance)))
	validate_duplicate_linked_internal_clearance(doc)


@frappe.whitelist()
def validate_duplicate_linked_internal_clearance(doc):
	linked_so = []
	if doc.sales_order_type == "Internal Clearance":
		for so in doc.sales_order_clearances:
			so_clearances = frappe.get_all("Sales Order Clearances", filters={
					"sales_order":so.sales_order, 
					"parent":["!=", doc.name],
					"docstatus": ["!=", 2]
				})
			if len(so_clearances) > 0:
				linked_so.append(so.sales_order)

	if len(linked_so) > 0:
		linked_so = " <br>".join(linked_so)
		frappe.throw("Cannot be linked because these Sales Order are already linked in Different Clearances <br> {0}".format(linked_so))



@frappe.whitelist()
def reset_internal_clearance_status(doc, handler=None):
	if doc.sales_order_type == "Internal Clearance":
		for so in doc.sales_order_clearances:
			so_doc = frappe.get_doc("Sales Order", so.sales_order)
			if so_doc.clearance_status == "Cleared":
				frappe.db.set_value(so_doc.doctype, so_doc.name, "clearance_status", "Not Cleared")


@frappe.whitelist()
def make_software_maintenance(source_name, target_doc=None):
	def postprocess(source, doc): # source = Sales Order, doc = Software Maintenance
		if source.sales_order_type == "First Sale":
			doc.first_sale_on = source.transaction_date
			for item in doc.items:
				item.start_date = item.start_date + timedelta(days=365)
				item.end_date = item.end_date + timedelta(days=365)
				days_diff = item.end_date - item.start_date
				if days_diff == 365:
					item.end_date = item.end_date - timedelta(days=1)
				so_item = source.items[item.idx-1]
				if so_item.item_type == "Maintenance Item":
					item.rate = so_item.reoccuring_maintenance_amount
					item.reoccuring_maintenance_amount = so_item.reoccuring_maintenance_amount
				else:
					item.rate = 0
					item.reoccuring_maintenance_amount = 0
		doc.assign_to = source.assigned_to

	doc = get_mapped_doc(
		"Sales Order",
		source_name,
		{
			"Sales Order": {
				"doctype": "Software Maintenance",
				"field_map": {
					"name": "sales_order",
				},
			},
			"Sales Order Item": {
				"doctype": "Software Maintenance Item",
			},
		},
		target_doc,
		postprocess,
	)

	return doc

@frappe.whitelist()
def update_internal_clearance_status(doc, handler=None):
	if doc.sales_order_type == "Internal Clearance":
		for item in doc.items:
			internal_so = doc.sales_order_clearances[item.idx - 1].get("sales_order")
			frappe.db.set_value(doc.doctype, internal_so, "clearance_status", "Cleared")


def update_software_maintenance(doc, method=None):
	if doc.get("software_maintenance"):
		software_maintenance = frappe.get_doc("Software Maintenance", doc.software_maintenance)
		if doc.sales_order_type not in ["Follow-Up Sale"]:
			if (doc.performance_period_start is not None and doc.performance_period_start != "") and (doc.performance_period_end is not None and doc.performance_period_end != ""):
				if software_maintenance.performance_period_start != doc.performance_period_start:
					software_maintenance.performance_period_start = doc.performance_period_start
				if software_maintenance.performance_period_end != doc.performance_period_end:
					software_maintenance.performance_period_end = doc.performance_period_end
			
		software_maintenance.sale_order = doc.name
		for item in doc.items:
			item_rate = item.rate
			item_reoccuring_maintenance_amount = item.reoccuring_maintenance_amount
			item_start_date = item.start_date
			item_end_date = item.end_date

			if doc.sales_order_type == "Reoccuring Maintenance":
				item_start_date = software_maintenance.performance_period_start
				item_end_date = software_maintenance.performance_period_end

			if item.item_type == "Maintenance Item":
				item_rate = item.reoccuring_maintenance_amount
			else:
				item_rate = 0
				item_reoccuring_maintenance_amount = 0
			if type(item_start_date) == str:
				item_start_date = datetime.strptime(item_start_date, "%Y-%m-%d").date()
			if type(item_end_date) == str:
				item_end_date = datetime.strptime(item_end_date, "%Y-%m-%d").date()
			item_start_date = item_start_date + timedelta(days=365)
			item_end_date = item_end_date + timedelta(days=365)
			if doc.sales_order_type == "Follow-Up Sale":
				item_end_date = software_maintenance.performance_period_end + timedelta(days=365)
				
				# Initialize a counter for months
				months_count = 0
				current_date = item_start_date
				# Loop through the months between start and end dates
				while current_date <= item_end_date:
					# Increment the month counter
					months_count += 1
					# Move to the next month
					current_date = current_date.replace(day=1)  # Move to the first day of the month
					current_date = current_date + relativedelta(months=1)  # Move to the next month

				# Total Months difference
				remaining_months = months_count
				# Calculating Per month rate by dividing it by 12
				per_month_rate = flt(item_rate / 12,2)
				# calculating total rate of calculated months
				total_remaining_item_rate = remaining_months * per_month_rate
				item_rate = total_remaining_item_rate

			days_diff = item_end_date - item_start_date
			if days_diff == 365:
				item_end_date = item_end_date - timedelta(days=1)

			software_maintenance.append("items", {
				"item_code": item.item_code,
				"item_name": item.item_name,
				"description": item.description,
				"start_date": item_start_date,
				"end_date": item_end_date,
				"price_list_rate": item.price_list_rate,
				"conversion_factor": item.conversion_factor,
				"item_language": item.item_language,
				"rate": item_rate,
				"reoccuring_maintenance_amount": item_reoccuring_maintenance_amount,
				"qty": item.qty,
				"uom": item.uom,
				"einkaufspreis": item.einkaufspreis
			})

		software_maintenance.save()


def create_followup_software_maintenance_sales_order(date=None):
	if not date:
		date = today()

	software_maintenance_list = frappe.db.sql("""
		SELECT name 
		FROM `tabSoftware Maintenance`
		WHERE DATE_SUB(performance_period_end, INTERVAL lead_time DAY) = %s
	""", date, as_dict=1)

	for software_maintenance in software_maintenance_list:
		try:
			make_sales_order(software_maintenance.name)
		except Exception as e:
			error_message = frappe.get_traceback()+"{0}\n".format(str(e))
			frappe.log_error(error_message, 'Error occured While automatically Software Maintenance Sales Order for {0}'.format(software_maintenance))
		finally:
			frappe.db.commit()


@frappe.whitelist()
def make_sales_order(software_maintenance, is_background_job=True):
	software_maintenance = frappe.get_doc("Software Maintenance", software_maintenance)
	if not software_maintenance.assign_to:
		frappe.throw(_("Please set 'Assign to' in Software maintenance '{0}'").format(software_maintenance.name))

	employee =  frappe.get_cached_value('Employee', {'user_id': software_maintenance.assign_to}, 'name')
	if not employee:
		frappe.throw(_("User {0} not set in Employee").format(software_maintenance.assign_to))
	old_start_date = software_maintenance.performance_period_start
	performance_period_start = add_days(software_maintenance.performance_period_end, 1)
	performance_period_end = add_years(performance_period_start, software_maintenance.maintenance_duration) - timedelta(days=1)
	total_days = getdate(performance_period_end) - getdate(performance_period_start)

	days_diff = total_days.days%365
	if days_diff != 0:
		_performance_period_end = add_days(performance_period_end, -days_diff)
		total_days = getdate(_performance_period_end) - getdate(performance_period_start)

	transaction_date = add_days(performance_period_end, -cint(software_maintenance.lead_time))
	sales_order = frappe.new_doc("Sales Order")
	sales_order.customer_subsidiary = software_maintenance.customer_subsidiary
	sales_order.performance_period_start = performance_period_start
	sales_order.performance_period_end = performance_period_end
	sales_order.software_maintenance = software_maintenance.name
	sales_order.item_group = software_maintenance.item_group
	sales_order.customer = software_maintenance.customer
	sales_order.sales_order_type = "Follow Up Maintenance"
	sales_order.ihr_ansprechpartner = employee
	sales_order.transaction_date = transaction_date
	sales_order.order_type = "Sales"

	for item in software_maintenance.items:
		start_date = performance_period_start
		item_rate = item.rate
		if item.start_date != old_start_date:
			per_day_rate = item.rate / 365
			start_date = item.end_date
			d0 = start_date
			d1 = performance_period_end
			delta = d1 - d0
			days_remaining = delta.days
			total_remaining_item_rate = days_remaining * per_day_rate
			item_rate = total_remaining_item_rate

		sales_order.append("items", {
			"item_code": item.item_code,
			"item_name": item.item_name,
			"description": item.description,
			"conversion_factor": item.conversion_factor,
			"qty": item.qty,
			"rate": item_rate,
			"uom": item.uom,
			"item_language": item.item_language,
			"delivery_date": sales_order.transaction_date,
			"start_date": start_date,
			"end_date": performance_period_end
		})

	sales_order.insert()

	if not cint(is_background_job):
		frappe.msgprint("Maintenance Duration (Years): {}".format(software_maintenance.maintenance_duration))
		frappe.msgprint("Maintenance Duration (Days): {}".format(total_days.days))
		frappe.msgprint(_("New {} Created").format(frappe.get_desk_link("Sales Order", sales_order.name)))
		
@frappe.whitelist()
def update_clearance_and_margin_amount(self, handler=None):
	if type(self) == str:
		self = frappe._dict(json.loads(self))
	"""Update Clearance Amount in Sales Order"""
	po_items = frappe.get_all("Purchase Order Item", filters={"sales_order": self.name}, fields="*")
	for item in po_items:
		if item.sales_order:
			po_total = frappe.db.get_value("Purchase Order", item.parent, "total")
			is_eligable_for_clearance = self.eligable_for_clearance
			internal_clearance_details = self.internal_clearance_details
			if is_eligable_for_clearance:
				if internal_clearance_details is not None and internal_clearance_details != "":
					internal_commision_rate = frappe.db.get_value("Internal Clearance Details", internal_clearance_details, "clearance_rate") or 0
					"""Clearance Comission (Z)
					Sales Order net amount (Y)
					Purchase Order net amount (X)
					Clearance Amount = ((Y) - (X)) * (1-(Z))"""

					so_margin_amount = self.total - po_total
					so_margin_percent = ((self.total - po_total)/self.total) * 100
					clearance_amount = (self.total - po_total) * (internal_commision_rate/100)
					return {"po_total": po_total, "so_margin": so_margin_amount, "so_margin_percent": so_margin_percent, "clearance_amount": clearance_amount}
				else:
					return {"po_total": po_total, "so_margin": 0, "so_margin_percent": 0, "clearance_amount": 0}