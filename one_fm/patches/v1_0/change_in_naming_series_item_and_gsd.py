from __future__ import unicode_literals
import frappe

def execute():
    # UNF-SHT-#### to UNF-SHT-######
	rename_item_according_to_new_series()

def rename_item_according_to_new_series():
    frappe.reload_doc('stock', 'doctype', 'item')
    old_item_code_field = False
    if frappe.db.has_column('Item', 'old_item_code'):
        old_item_code_field = True
    for doc in frappe.get_all('Item', filters={'subitem_group': 'Uniforms'}):
        if len(doc.name)==12:
            _doc = frappe.get_doc('Item', doc.name)
            if old_item_code_field:
                _doc.old_item_code = doc.name
            subitem_group_code = frappe.db.get_value('Item Group', _doc.subitem_group, 'one_fm_item_group_abbr')
            item_group_code = frappe.db.get_value('Item Group', _doc.item_group, 'one_fm_item_group_abbr')
            new_item_code = subitem_group_code+"-"+item_group_code+"-"+"00"+doc.name[-4:]
            _doc.item_code = new_item_code
            _doc.item_name = new_item_code
            _doc.item_barcode = new_item_code
            _doc.item_id = "00"+doc.name[-4:]
            _doc.save(ignore_permissions=True)
            frappe.rename_doc('Item', doc.name, new_item_code, force=True)
            print(doc.name)
            print(new_item_code)
