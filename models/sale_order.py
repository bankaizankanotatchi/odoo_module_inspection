# models/sale_order.py
from odoo import models, fields, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

     
    contact = fields.Many2one('res.partner', string="Contact")
    description = fields.Char(string='Objet de la commande')
    x_studio_objet = fields.Char(string='Objet')
    department_id = fields.Many2one('product.category', string="Département", required=True)


    
    @api.onchange('order_line')
    def _onchange_order_line_category(self):
        """Définir automatiquement le département et l'objet de la commande"""
        if self.order_line:
            first_line = self.order_line[0]
            self.department_id = first_line.product_id.categ_id

            # Si catégorie contient "formation"
            if self.department_id and 'formation' in self.department_id.name.lower():
                if not self.description:
                    self.description = ("Formation en " + first_line.product_id.name).upper()

            # Si catégorie contient "inspection"
            elif self.department_id and 'inspection' in self.department_id.name.lower():
                if not self.description:
                    self.description = ("Inspection en " + first_line.product_id.name).upper()


    def action_confirm(self):
        """Surcharge de la confirmation de commande pour créer auto l'affaire"""
        res = super(SaleOrder, self).action_confirm()
        
        for order in self:
            # Vérifie chaque ligne de produit pour trouver une catégorie "inspection"
            for line in order.order_line:
                if line.product_id.categ_id and 'inspection' in line.product_id.categ_id.name.lower():
                    self.env['kes_inspections.affaire'].create_from_sale_order(order)
                    break  # Une seule affaire par commande
        
        return res

    # Champ computed pour afficher le compte des affaires liées
    inspection_affaire_count = fields.Integer(
        string="Affaires d'Inspection",
        compute='_compute_inspection_affaire_count'
    )

    def _compute_inspection_affaire_count(self):
        for order in self:
            order.inspection_affaire_count = self.env['kes_inspections.affaire'].search_count([
                ('sale_order_id', '=', order.id)
            ])

    def action_open_inspection_affaire(self):
        """Ouvre l'affaire d'inspection liée à cette commande"""
        self.ensure_one()
        affaire = self.env['kes_inspections.affaire'].search([
            ('sale_order_id', '=', self.id)
        ], limit=1)
        
        if affaire:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Affaire dInspection',
                'res_model': 'kes_inspections.affaire',
                'res_id': affaire.id,
                'view_mode': 'form',
                'target': 'current',
            }