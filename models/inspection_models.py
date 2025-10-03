from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta

class InspectionAffaire(models.Model):
    _name = 'kes_inspections.affaire'
    _description = 'Affaire dInspection'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    
    name = fields.Char(string='Référence', required=True, copy=False, readonly=True, default='Nouvelle')
    sale_order_id = fields.Many2one('sale.order', string='Commande liée', readonly=True)
    client_id = fields.Many2one('res.partner', string='Client', required=True, readonly=True)
    
    # 🔹 NOUVEAUX CHAMPS DATE
    date_debut_intervention = fields.Date(string='Date début intervention terrain')
    date_fin_intervention = fields.Date(string='Date fin intervention terrain')
    date_debut_redaction = fields.Date(string='Date début rédaction rapport')
    date_fin_redaction = fields.Date(string='Date fin rédaction rapport')
    
    # 🔹 NOUVEAUX CHAMPS LIEU
    site_intervention = fields.Char(string='Site d\'intervention')
    lieu_intervention = fields.Char(string='Lieu d\'intervention spécifique')
    
    # 🔹 CHARGÉ D'AFFAIRE DEPUIS EMPLOYÉS INSPECTION
    charge_affaire_id = fields.Many2one(
        'hr.employee',
        string='Chargé d\'affaire',
        domain=[('department_id.name', '=', 'INSPECTION')],
        required=True
    )

    # 🔹 SOUS-TRAITANT
    sous_traitant_utilise = fields.Boolean(string='Utilisation sous-traitant', default=False)
    sous_traitant_id = fields.Many2one(
        'res.partner',
        string='Sous-traitant',
        domain=[('company_type', '=', 'company')]  # Seulement les entreprises
    )
    
    # 🔹 ALERTE PROCHAINE INSPECTION
    alerte_prochaine_inspection = fields.Selection([
        ('6mois', '6 mois'),
        ('1an', '1 an'),
        ('2ans', '2 ans'),
        ('3ans', '3 ans'),
    ], string='Alerte prochaine inspection', default='1an', tracking=True)
    
    date_prochaine_inspection = fields.Date(
        string='Date prochaine inspection',
        compute='_compute_date_prochaine_inspection',
        store=True
    )
    
    # 🔹 DÉPARTEMENT DEPUIS LA VENTE
    department_id = fields.Many2one(
        'product.category', 
        string='Département',
        related='sale_order_id.department_id',
        store=True,
        readonly=True
    )
    
    # Relations existantes (à conserver)
    inspecteur_ids = fields.Many2many('kes_inspections.inspecteur', string='Inspecteurs assignés')
    rapport_affaire_ids = fields.One2many('kes_inspections.rapport.affaire', 'affaire_id', string='Rapports liés')
    qrcode_affaire = fields.Binary(string="QR Code de l'affaire", readonly=True)
    type_inspection = fields.Char(string='Type(s) dInspection', compute='_compute_type_inspection', store=True)
    order_date = fields.Datetime(string='Date de création', related='sale_order_id.date_order', store=True, readonly=True)
    
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('in_progress', 'En cours'),
        ('done', 'Terminée'),
    ], default='draft', string='Statut', tracking=True)
    
    sous_affaire_ids = fields.One2many('kes_inspections.sous_affaire', 'affaire_id', string='Sous-affaires')
    sous_affaire_count = fields.Integer(string='Nombre de sous-affaires', compute='_compute_sous_affaire_count')
    
    equipement_ids = fields.One2many('kes_inspections.equipement', 'affaire_id', string='Équipements à inspecter')
    equipement_count = fields.Integer(string='Nombre déquipements', compute='_compute_equipement_count')
    total_etiquettes = fields.Integer(string='Total étiquettes', compute='_compute_total_etiquettes')
    inspecteur_count = fields.Integer(string="Nombre d'inspecteurs", compute='_compute_inspecteur_count')
    rapport_affaire_count = fields.Integer(string="Nombre de rapports", compute='_compute_rapport_affaire_count')

    # ─────────────────────────────────────────────────────────────
    # 🔸 MÉTHODES DE CALCUL
    # ─────────────────────────────────────────────────────────────
    
    @api.depends('date_fin_intervention', 'alerte_prochaine_inspection')
    def _compute_date_prochaine_inspection(self):
        """Calcule la date de la prochaine inspection basée sur l'alerte"""
        for affaire in self:
            if affaire.date_fin_intervention and affaire.alerte_prochaine_inspection:
                base_date = affaire.date_fin_intervention
                if affaire.alerte_prochaine_inspection == '6mois':
                    affaire.date_prochaine_inspection = base_date + timedelta(days=180)
                elif affaire.alerte_prochaine_inspection == '1an':
                    affaire.date_prochaine_inspection = base_date + timedelta(days=365)
                elif affaire.alerte_prochaine_inspection == '2ans':
                    affaire.date_prochaine_inspection = base_date + timedelta(days=730)
                elif affaire.alerte_prochaine_inspection == '3ans':
                    affaire.date_prochaine_inspection = base_date + timedelta(days=1095)
            else:
                affaire.date_prochaine_inspection = False

    @api.depends('sale_order_id', 'sale_order_id.order_line')
    def _compute_type_inspection(self):
        for affaire in self:
            if affaire.sale_order_id and affaire.sale_order_id.order_line:
                types = affaire.sale_order_id.order_line.mapped('product_id.name')
                affaire.type_inspection = ', '.join(set(types)) if types else 'Générique'
            else:
                affaire.type_inspection = 'Générique'

    @api.depends('sous_affaire_ids')
    def _compute_sous_affaire_count(self):
        for affaire in self:
            affaire.sous_affaire_count = len(affaire.sous_affaire_ids)

    @api.depends('equipement_ids')
    def _compute_equipement_count(self):
        for affaire in self:
            affaire.equipement_count = len(affaire.equipement_ids)

    @api.depends('equipement_ids.nombre_etiquettes')
    def _compute_total_etiquettes(self):
        for affaire in self:
            affaire.total_etiquettes = sum(equipement.nombre_etiquettes for equipement in affaire.equipement_ids)

    @api.depends('inspecteur_ids')
    def _compute_inspecteur_count(self):
        for affaire in self:
            affaire.inspecteur_count = len(affaire.inspecteur_ids)

    @api.depends('rapport_affaire_ids')
    def _compute_rapport_affaire_count(self):
        for affaire in self:
            affaire.rapport_affaire_count = len(affaire.rapport_affaire_ids)

    # ─────────────────────────────────────────────────────────────
    # 🔸 MÉTHODES CRUD
    # ─────────────────────────────────────────────────────────────
    
    @api.model
    def create(self, vals):
        if not vals.get('name') or vals['name'] == 'Nouvelle':
            order_ref = ''
            if vals.get('sale_order_id'):
                order = self.env['sale.order'].browse(vals['sale_order_id'])
                order_ref = order.name or ''
            
            last_affaire = self.search([], order='id desc', limit=1)
            next_num = (int(last_affaire.name.split('/I')[-1]) + 1) if last_affaire and '/I' in last_affaire.name else 1
            inspection_seq = str(next_num).zfill(3)
            
            vals['name'] = f"{order_ref}/I{inspection_seq}" if order_ref else f"I{inspection_seq}"
        
        return super(InspectionAffaire, self).create(vals)

    @api.model
    def create_from_sale_order(self, order):
        """Crée une affaire depuis une commande de vente"""
        for line in order.order_line:
            if line.product_id.categ_id and 'inspection' in line.product_id.categ_id.name.lower():
                existing = self.search([('sale_order_id', '=', order.id)], limit=1)
                if not existing:
                    # Trouver un chargé d'affaire par défaut
                    charge_affaire = self.env['hr.employee'].search([
                        ('department_id.name', '=', 'INSPECTION')
                    ], limit=1)
                    
                    return self.create({
                        'sale_order_id': order.id,
                        'client_id': order.partner_id.id,
                        'site_intervention': order.partner_id.name or 'Site client',
                        'charge_affaire_id': charge_affaire.id if charge_affaire else False,
                    })
        return False

    # ─────────────────────────────────────────────────────────────
    # 🔸 ACTIONS
    # ─────────────────────────────────────────────────────────────
    
    def action_view_sous_affaires(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Sous-affaires - {self.name}',
            'res_model': 'kes_inspections.sous_affaire',
            'view_mode': 'list,form,kanban',
            'domain': [('affaire_id', '=', self.id)],
            'context': {'default_affaire_id': self.id}
        }

    def action_view_equipements(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Équipements - {self.name}',
            'res_model': 'kes_inspections.equipement',
            'view_mode': 'list,form,kanban',
            'domain': [('affaire_id', '=', self.id)],
            'context': {'default_affaire_id': self.id}
        }

    def action_view_rapport_affaire(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Rapports - {self.name}',
            'res_model': 'kes_inspections.rapport.affaire',
            'view_mode': 'list,form,kanban',
            'domain': [('affaire_id', '=', self.id)],
            'context': {'default_affaire_id': self.id}
        }

    def action_view_inspecteurs(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Inspecteurs',
            'res_model': 'kes_inspections.inspecteur',
            'view_mode': 'list,form,kanban',
            'domain': [('id', 'in', self.inspecteur_ids.ids)],
            'context': {'default_affaire_ids': [(6, 0, [self.id])]},
        }

    def action_generer_toutes_etiquettes(self):
        self.ensure_one()
        equipements = self.equipement_ids.filtered(lambda e: not e.etiquettes_generes)
        for equipement in equipements:
            equipement.action_generer_etiquettes()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Étiquettes générées',
                'message': f'Étiquettes générées pour {len(equipements)} équipement(s)',
                'sticky': False,
            }
        }

# Surcharge Sale Order
class SaleOrder(models.Model):
    _inherit = 'sale.order'

    inspection_affaire_count = fields.Integer(
        string="Affaires d'Inspection",
        compute='_compute_inspection_affaire_count'
    )

    def _compute_inspection_affaire_count(self):
        for order in self:
            order.inspection_affaire_count = self.env['kes_inspections.affaire'].search_count([
                ('sale_order_id', '=', order.id)
            ])

    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        for order in self:
            for line in order.order_line:
                if line.product_id.categ_id and 'inspection' in line.product_id.categ_id.name.lower():
                    self.env['kes_inspections.affaire'].create_from_sale_order(order)
                    break
        return res

    def action_open_inspection_affaire(self):
        self.ensure_one()
        affaire = self.env['kes_inspections.affaire'].search([('sale_order_id', '=', self.id)], limit=1)
        if affaire:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Affaire dInspection',
                'res_model': 'kes_inspections.affaire',
                'res_id': affaire.id,
                'view_mode': 'form',
                'target': 'current',
            }