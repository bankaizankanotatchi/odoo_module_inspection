# -*- coding: utf-8 -*-
# from odoo import http


# class KesInspections(http.Controller):
#     @http.route('/kes_inspections/kes_inspections', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/kes_inspections/kes_inspections/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('kes_inspections.listing', {
#             'root': '/kes_inspections/kes_inspections',
#             'objects': http.request.env['kes_inspections.kes_inspections'].search([]),
#         })

#     @http.route('/kes_inspections/kes_inspections/objects/<model("kes_inspections.kes_inspections"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('kes_inspections.object', {
#             'object': obj
#         })

