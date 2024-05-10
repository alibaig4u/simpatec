import frappe

def execute():
	"""Query for removing all previous Software maintenance Items"""
	frappe.db.sql("DELETE FROM `tabSoftware Maintenance Item`")
	frappe.db.commit()