import json
import frappe
from frappe import _
from frappe.utils import cint, cstr, flt, add_days, add_years, today, getdate
from frappe.model.mapper import get_mapped_doc
from datetime import date, timedelta, datetime
from dateutil.relativedelta import relativedelta
from six import string_types

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
	validate_maintenance_amount(doc)


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
					item.rate = so_item.reoccurring_maintenance_amount
					item.reoccurring_maintenance_amount = so_item.reoccurring_maintenance_amount
				else:
					item.rate = 0
					item.reoccurring_maintenance_amount = 0
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
			if len(doc.sales_order_clearances) > 0:
				internal_so = doc.sales_order_clearances[item.idx - 1].get("sales_order")
				frappe.db.set_value(doc.doctype, internal_so, "clearance_status", "Cleared")
			else:
				frappe.throw("Sales Order Type 'Internal Clearance' is selected, the sales order clearance cannot be empty.")


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
		if doc.sales_order_type == "Reoccuring Maintenance":
			software_maintenance.items = []
		for item in doc.items:
			if item.item_type == "Inflation Item":
				continue
			item_rate = item.rate
			item_reoccurring_maintenance_amount = item.reoccurring_maintenance_amount
			item_start_date = item.start_date
			item_end_date = item.end_date

			
			if item.item_type == "Maintenance Item":
				item_rate = item.reoccurring_maintenance_amount
			else:
				item_rate = 0
				item.price_list_rate = 0
				item_reoccuring_maintenance_amount = 0
			if type(item_start_date) == str:
				item_start_date = datetime.strptime(item_start_date, "%Y-%m-%d").date()
			if type(item_end_date) == str:
				item_end_date = datetime.strptime(item_end_date, "%Y-%m-%d").date()
			item_start_date = item_start_date + timedelta(days=365)
			item_end_date = item_end_date + timedelta(days=365)

			if doc.sales_order_type == "Reoccuring Maintenance":
				item_start_date = software_maintenance.performance_period_start
				item_end_date = software_maintenance.performance_period_end
			elif doc.sales_order_type == "Follow-Up Sale":
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
			# Convert start and end dates to date objects if they're strings
			item_start_date = item_start_date
			item_end_date = item_end_date
			if isinstance(item_start_date, str):
				item_start_date = datetime.strptime(item_start_date, "%Y-%m-%d").date()
			if isinstance(item_end_date, str):
				item_end_date = datetime.strptime(item_end_date, "%Y-%m-%d").date()

			days_diff = item_end_date - item_start_date
			if days_diff == 365:
				item_end_date = item_end_date - timedelta(days=1)

			software_maintenance.append("items", {
				"item_code": item.item_code,
				"item_name": item.item_name,
				"item_name_en": item.item_name_en,
				"item_name_de": item.item_name_de,
				"item_name_fr": item.item_name_fr,
				"description": item.description,
				"item_language": item.item_language,
				"item_description_en": item.item_description_en,
				"item_description_de": item.item_description_de,
				"item_description_fr": item.item_description_fr,
				"start_date": item_start_date,
				"end_date": item_end_date,
				"price_list_rate": item.price_list_rate,
				"conversion_factor": item.conversion_factor,
				"item_language": item.item_language,
				"rate": item_rate,
				"reoccurring_maintenance_amount": item_reoccurring_maintenance_amount,
				"qty": item.qty,
				"uom": item.uom,
				"purchase_price": item.purchase_price,
				"sales_order": doc.name
			})

		software_maintenance.save()


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
				
@frappe.whitelist()
def make_purchase_order_for_default_supplier(source_name, selected_items=None, target_doc=None):
	"""Creates Purchase Order for each Supplier. Returns a list of doc objects."""

	from erpnext.setup.utils import get_exchange_rate

	if not selected_items:
		return

	if isinstance(selected_items, string_types):
		selected_items = json.loads(selected_items)

	def set_missing_values(source, target):
		target.supplier = supplier
		target.currency = frappe.db.get_value(
			"Supplier", filters={"name": supplier}, fieldname=["default_currency"]
		)
		company_currency = frappe.db.get_value(
			"Company", filters={"name": target.company}, fieldname=["default_currency"]
		)

		target.conversion_rate = get_exchange_rate(target.currency, company_currency, args="for_buying")

		target.apply_discount_on = ""
		target.additional_discount_percentage = 0.0
		target.discount_amount = 0.0
		target.inter_company_order_reference = ""
		target.shipping_rule = ""

		default_price_list = frappe.get_value("Supplier", supplier, "default_price_list")
		if default_price_list:
			target.buying_price_list = default_price_list

		if any(item.delivered_by_supplier == 1 for item in source.items):
			if source.shipping_address_name:
				target.shipping_address = source.shipping_address_name
				target.shipping_address_display = source.shipping_address
			else:
				target.shipping_address = source.customer_address
				target.shipping_address_display = source.address_display

			target.customer_contact_person = source.contact_person
			target.customer_contact_display = source.contact_display
			target.customer_contact_mobile = source.contact_mobile
			target.customer_contact_email = source.contact_email

		else:
			target.customer = ""
			target.customer_name = ""

		target.run_method("set_missing_values")
		target.run_method("calculate_taxes_and_totals")

	def update_item(source, target, source_parent):
		target.schedule_date = source.delivery_date
		target.qty = flt(source.qty) - (flt(source.ordered_qty) / flt(source.conversion_factor))
		target.stock_qty = flt(source.stock_qty) - flt(source.ordered_qty)
		target.project = source_parent.project

	suppliers = [item.get("supplier") for item in selected_items if item.get("supplier")]
	suppliers = list(dict.fromkeys(suppliers))  # remove duplicates while preserving order

	items_to_map = [item.get("item_code") for item in selected_items if item.get("item_code")]
	items_to_map = list(set(items_to_map))

	if not suppliers:
		frappe.throw(
			_("Please set a Supplier against the Items to be considered in the Purchase Order.")
		)

	purchase_orders = []
	for supplier in suppliers:
		doc = get_mapped_doc(
			"Sales Order",
			source_name,
			{
				"Sales Order": {
					"doctype": "Purchase Order",
					"field_no_map": [
						"address_display",
						"contact_display",
						"contact_mobile",
						"contact_email",
						"contact_person",
						"taxes_and_charges",
						"shipping_address",
						"terms",
					],
					"validation": {"docstatus": ["=", 1]},
				},
				"Sales Order Item": {
					"doctype": "Purchase Order Item",
					"field_map": [
						["name", "sales_order_item"],
						["parent", "sales_order"],
						["stock_uom", "stock_uom"],
						["uom", "uom"],
						["conversion_factor", "conversion_factor"],
						["delivery_date", "schedule_date"],
					],
					"field_no_map": [
						"rate",
						"price_list_rate",
						"item_tax_template",
						"discount_percentage",
						"discount_amount",
						"pricing_rules",
					],
					"postprocess": update_item,
					"condition": lambda doc: doc.ordered_qty < doc.stock_qty
					and doc.supplier == supplier
					and doc.item_code in items_to_map,
				},
			},
			target_doc,
			set_missing_values,
		)

		doc.insert()
		frappe.db.commit()
		purchase_orders.append(doc)

	return purchase_orders


@frappe.whitelist()
def make_purchase_order(source_name, selected_items=None, target_doc=None):
	if not selected_items:
		return

	if isinstance(selected_items, string_types):
		selected_items = json.loads(selected_items)

	items_to_map = [
		item.get("item_code")
		for item in selected_items
		if item.get("item_code") and item.get("item_code")
	]
	items_to_map = list(set(items_to_map))

	def is_drop_ship_order(target):
		drop_ship = True
		for item in target.items:
			if not item.delivered_by_supplier:
				drop_ship = False
				break

		return drop_ship

	def set_missing_values(source, target):
		target.supplier = ""
		target.apply_discount_on = ""
		target.additional_discount_percentage = 0.0
		target.discount_amount = 0.0
		target.inter_company_order_reference = ""
		target.shipping_rule = ""

		if is_drop_ship_order(target):
			target.customer = source.customer
			target.customer_name = source.customer_name
			target.shipping_address = source.shipping_address_name
		else:
			target.customer = target.customer_name = target.shipping_address = None

		target.run_method("set_missing_values")
		target.run_method("calculate_taxes_and_totals")

	def update_item(source, target, source_parent):
		target.schedule_date = source.delivery_date
		target.qty = flt(source.qty) - (flt(source.ordered_qty) / flt(source.conversion_factor))
		target.stock_qty = flt(source.stock_qty) - flt(source.ordered_qty)
		target.project = source_parent.project
		target.rate = source.purchase_price
		target.price_list_rate = source.purchase_price

	def update_item_for_packed_item(source, target, source_parent):
		target.qty = flt(source.qty) - flt(source.ordered_qty)

	# po = frappe.get_list("Purchase Order", filters={"sales_order":source_name, "supplier":supplier, "docstatus": ("<", "2")})
	doc = get_mapped_doc(
		"Sales Order",
		source_name,
		{
			"Sales Order": {
				"doctype": "Purchase Order",
				"field_no_map": [
					"address_display",
					"contact_display",
					"contact_mobile",
					"contact_email",
					"contact_person",
					"taxes_and_charges",
					"shipping_address",
					"terms",
				],
				"validation": {"docstatus": ["=", 1]},
			},
			"Sales Order Item": {
				"doctype": "Purchase Order Item",
				"field_map": [
					["name", "sales_order_item"],
					["parent", "sales_order"],
					["stock_uom", "stock_uom"],
					["uom", "uom"],
					["conversion_factor", "conversion_factor"],
					["delivery_date", "schedule_date"],
				],
				"field_no_map": [
					"rate",
					"price_list_rate",
					"item_tax_template",
					"discount_percentage",
					"discount_amount",
					"supplier",
					"pricing_rules",
				],
				"postprocess": update_item,
				"condition": lambda doc: doc.ordered_qty < doc.stock_qty
				and doc.item_code in items_to_map
				and not is_product_bundle(doc.item_code),
			},
			"Packed Item": {
				"doctype": "Purchase Order Item",
				"field_map": [
					["name", "sales_order_packed_item"],
					["parent", "sales_order"],
					["uom", "uom"],
					["conversion_factor", "conversion_factor"],
					["parent_item", "product_bundle"],
					["rate", "rate"],
				],
				"field_no_map": [
					"price_list_rate",
					"item_tax_template",
					"discount_percentage",
					"discount_amount",
					"supplier",
					"pricing_rules",
				],
				"postprocess": update_item_for_packed_item,
				"condition": lambda doc: doc.parent_item in items_to_map,
			},
		},
		target_doc,
		set_missing_values,
	)

	set_delivery_date(doc.items, source_name)

	return doc


def is_product_bundle(item_code):
	return frappe.db.exists("Product Bundle", item_code)


def set_delivery_date(items, sales_order):
	delivery_dates = frappe.get_all(
		"Sales Order Item", filters={"parent": sales_order}, fields=["delivery_date", "item_code"]
	)

	delivery_by_item = frappe._dict()
	for date in delivery_dates:
		delivery_by_item[date.item_code] = date.delivery_date

	for item in items:
		if item.product_bundle:
			item.schedule_date = delivery_by_item[item.product_bundle]


@frappe.whitelist()
def validate_maintenance_amount(doc):
	if doc.docstatus == 0:
		row = []
		for item in doc.items:
			if item.reoccurring_maintenance_amount <= 0 and item.item_type == "Maintenance Item":
				row.append(_(f"<li>{_('Row')} {item.idx}</li>"))
		if len(row) > 0:
			row = "".join(row)
			msg = f"{_('One or more maintenance items in the Sales Order Item table have an amount that is less than or equal to 0.00. Please review these items to ensure this is correct.')} <ul >{row}</ul>"
			frappe.msgprint(msg, title=_("Warning: Invalid Maintenance Amount"))