# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import today, month_diff
from frappe import _
from erpnext.stock.get_item_details import get_item_details

class EmployeeUniform(Document):
	def before_insert(self):
		if self.type == 'Return':
			self.naming_series = 'EUR-.YYYY.-'
		else:
			self.naming_series = 'EUI-.YYYY.-'

	def on_submit(self):
		if self.type == "Issue":
			self.status = 'Issued'
			self.issued_on = today()
		elif self.type == "Return":
			self.status = 'Returned'
			self.returned_on = today()
			for item in self.uniforms:
				if item.issued_item_link:
					returned = frappe.db.get_value('Employee Uniform Item', item.issued_item_link, 'returned')
					frappe.db.set_value('Employee Uniform Item', item.issued_item_link, 'returned', returned+item.quantity)

	def validate(self):
		if not self.uniforms:
			frappe.throw(_("Uniforms required in Employee Uniform"))
		self.validate_issue()
		self.validate_return()

	def validate_issue(self):
		self.validate_issued_items_are_returned()

	def validate_issued_items_are_returned(self):
		pass

	def validate_return(self):
		if self.type == 'Return':
			if not self.reason_for_return:
				frappe.throw(_("Reason for Return required in Employee Uniform"))
			self.validate_item_return_before_expiry()
			if self.reason_for_return in ['Item Damage', 'Employee Exit']:
				self.calculate_amount_pay_back()

	def validate_item_return_before_expiry(self):
		if self.reason_for_return in ['Item Damage', 'Item Expired']:
			pass

	def calculate_amount_pay_back(self):
		pay_back = 0
		for item in self.uniforms:
			if item.expire_on > self.returned_on:
				per_month_rate = (item.quantity * item.rate) / month_diff(item.expire_on, item.issued_on)
				pay_back += per_month_rate * month_diff(item.expire_on, self.returned_on)
		self.pay_back_to_company = pay_back

	def set_uniform_details(self):
		uniforms = False
		if self.employee:
			if self.type == "Issue" and self.designation:
				uniforms = get_project_uniform_details(self.designation, self.project)
				if not uniforms:
					frappe.msgprint(msg = 'No Designation Uniform Profile Found',
				       title = 'Warning',
				       indicator = 'red'
				    )
			elif self.type == "Return":
				uniforms = get_items_to_return(self.employee)

		if uniforms:
			for uniform in uniforms:
				unifrom_issue_ret = self.append('uniforms')
				unifrom_issue_ret.item = uniform.item
				unifrom_issue_ret.item_name = uniform.item_name
				unifrom_issue_ret.quantity = uniform.quantity
				unifrom_issue_ret.uom = uniform.uom
				if self.type == "Issue":
					args = {
						'item_code': uniform.item,
						'doctype': self.doctype,
						'buying_price_list': frappe.defaults.get_defaults().buying_price_list,
						'currency': frappe.defaults.get_defaults().currency,
						'name': self.name,
						'qty': uniform.quantity,
						'company': self.company,
						'conversion_rate': 1,
						'plc_conversion_rate': 1
					}
					unifrom_issue_ret.rate = get_item_details(args).price_list_rate
					if self.issued_on:
						unifrom_issue_ret.expire_on = frappe.utils.add_months(self.issued_on, 12)
				elif self.type == "Return":
					unifrom_issue_ret.expire_on = uniform.expire_on
					unifrom_issue_ret.rate = uniform.rate
					unifrom_issue_ret.issued_item_link = uniform.issued_item_link
					unifrom_issue_ret.issued_on = uniform.issued_on

def get_project_uniform_details(designation_id, project_id=''):
	if frappe.db.get_value('Designation', designation_id, 'one_fm_is_uniform_needed_for_this_job'):
		filters = {'designation': designation_id, 'project': project_id}
		query = """
			select
				name
			from
				`tabDesignation Uniform Profile`
			where
				designation=%(designation)s {condition}
		"""

		condition = "and project IS NULL"
		if project_id:
			condition = "and project=%(project)s"

		profile_id = frappe.db.sql(query.format(condition=condition), filters, as_dict=1)
		if not profile_id and project_id:
			condition = "and project IS NULL"
			profile_id = frappe.db.sql(query.format(condition=condition), filters, as_dict=1)
		if profile_id and profile_id[0]['name']:
			profile = frappe.get_doc('Designation Uniform Profile', profile_id[0]['name'])
			return profile.uniforms if profile.uniforms else False
	return False

def get_items_to_return(employee_id):
	return get_issued_items_not_returned(employee_id)

def get_issued_items_not_returned(employee_id):
	query = """
		select
			i.item, i.item_name, (i.quantity - i.returned) as quantity, i.uom, i.expire_on, i.rate,
			i.name as issued_item_link, u.issued_on
		from
			`tabEmployee Uniform Item` i, `tabEmployee Uniform` u
		where
			i.parent=u.name and u.employee = %(employee)s and i.returned < i.quantity and u.type = 'Issue'
			and u.docstatus = 1
	"""
	return frappe.db.sql(query,{'employee': employee_id}, as_dict=True)

def issued_items_not_returned(doctype, txt, searchfield, start, page_len, filters):
	query = """
		select
			i.item, i.item_name
		from
			`tabEmployee Uniform Item` i, `tabEmployee Uniform` u
		where
			i.parent=u.name and u.employee = %(employee)s and i.returned < i.quantity and u.type = 'Issue'
			and u.docstatus = 1 and (i.item like %(txt)s or i.item_name like %(txt)s)
			limit %(start)s, %(page_len)s"""
	return frappe.db.sql(query,
		{
			'employee': filters.get("employee"),
			'start': start,
			'page_len': page_len,
			'txt': "%%%s%%" % txt
		}
	)
