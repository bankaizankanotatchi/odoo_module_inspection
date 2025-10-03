from odoo import models, fields, api
from odoo.exceptions import ValidationError

class InspectionSousAffaire(models.Model):
    _name = 'kes_inspections.sous_affaire'
    _description = 'Sous-affaire dInspection'
    _order = 'create_date desc'
    
    # 🔹 CHAMPS PRINCIPAUX SIMPLIFIÉS
    name = fields.Char(string='Référence sous-affaire', required=True, copy=False, default='Nouvelle')
    affaire_id = fields.Many2one('kes_inspections.affaire', string='Affaire parente', required=True, ondelete='cascade')
    description = fields.Text(string='Description')
    date_creation = fields.Datetime(string='Date création', default=fields.Datetime.now, readonly=True)

    # 🔹 DOCUMENTS UNIQUES (1 par sous-affaire)
    bond_commande_ids = fields.One2many(
        'kes_inspections.bond_commande',
        'sous_affaire_id',
        string='Bond de commande',
    )

    pv_ids = fields.One2many(
        'kes_inspections.pv',
        'sous_affaire_id',
        string='Procès-verbaux',
    )

    enquete_satisfaction_ids = fields.One2many(
        'kes_inspections.enquete_satisfaction',
        'sous_affaire_id',
        string='Enquêtes de satisfaction',
    )

    
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('in_progress', 'En cours'),
        ('done', 'Terminée'),
    ], default='draft', string='Statut', tracking=True)
    
    # 🔹 CHARGÉ D'AFFAIRE PRINCIPAL (LIÉ À L'AFFAIRE)
    charge_affaire_principal = fields.Many2one(
        'hr.employee',
        string='Chargé d\'affaire principal',
        related='affaire_id.charge_affaire_id',
        readonly=True
    )

    produit_etiquette_ids = fields.One2many(
        'kes_inspections.sous_affaire_produit',
        'sous_affaire_id',
        string='Génération d\'étiquettes par produit'
    )
    
    # 🔹 INSPECTEURS ASSIGNÉS (NOUVEAU MODÈLE)
    inspecteur_ids = fields.One2many(
        'kes_inspections.sous_affaire_inspecteur',
        'sous_affaire_id',
        string='Inspecteurs assignés'
    )
    
    # 🔹 RÉSUMÉ DE LA MISSION
    point_focal_client_id = fields.Many2one(
        'res.partner',
        string='Point focal client',
        domain="[('parent_id', '=', client_id)]"
    )
    site_intervention = fields.Char(string='Site d\'intervention', related='affaire_id.site_intervention', readonly=True)
    lieu_intervention = fields.Char(string='Lieu', related='affaire_id.lieu_intervention', readonly=True)
    description_mission = fields.Text(string='Description de la mission')
    
    # 🔹 TYPES D'INTERVENTION (PRODUITS DE LA COMMANDE)
    type_intervention_ids = fields.Many2many(
        'product.product',
        string='Types d\'intervention',
        compute='_compute_types_intervention',
        store=True
    )

    # 🔹 RELATIONS EXISTANTES
    etiquette_ids = fields.One2many('kes_inspections.etiquette', 'sous_affaire_id', string='Étiquettes')
    rapport_ids = fields.One2many('kes_inspections.rapport', 'sous_affaire_id', string='Rapports')
    
    # 🔹 COMPTEURS
    etiquette_count = fields.Integer(string='Nombre d\'étiquettes', compute='_compute_etiquette_count')
    rapport_count = fields.Integer(string='Nombre de rapports', compute='_compute_rapport_count')
    inspecteur_count = fields.Integer(string='Nombre d\'inspecteurs', compute='_compute_inspecteur_count')

    # ─────────────────────────────────────────────────────────────
    # 🔸 MÉTHODES DE CALCUL
    # ─────────────────────────────────────────────────────────────
    
    @api.depends('affaire_id', 'affaire_id.sale_order_id', 'affaire_id.sale_order_id.order_line')
    def _compute_types_intervention(self):
        """Récupère les produits de la commande de vente liée"""
        for sous_affaire in self:
            if sous_affaire.affaire_id and sous_affaire.affaire_id.sale_order_id:
                products = sous_affaire.affaire_id.sale_order_id.order_line.mapped('product_id')
                sous_affaire.type_intervention_ids = [(6, 0, products.ids)]
            else:
                sous_affaire.type_intervention_ids = [(5, 0, 0)]

    @api.depends('etiquette_ids')
    def _compute_etiquette_count(self):
        for sous_affaire in self:
            sous_affaire.etiquette_count = len(sous_affaire.etiquette_ids)

    @api.depends('rapport_ids')
    def _compute_rapport_count(self):
        for sous_affaire in self:
            sous_affaire.rapport_count = len(sous_affaire.rapport_ids)

    @api.depends('inspecteur_ids')
    def _compute_inspecteur_count(self):
        for sous_affaire in self:
            sous_affaire.inspecteur_count = len(sous_affaire.inspecteur_ids)

    # ─────────────────────────────────────────────────────────────
    # 🔸 MÉTHODES CRUD
    # ─────────────────────────────────────────────────────────────
    
    @api.model
    def create(self, vals):
        if vals.get('name', 'Nouvelle') == 'Nouvelle':
            if vals.get('affaire_id'):
                affaire = self.env['kes_inspections.affaire'].browse(vals['affaire_id'])
                existing_count = self.search_count([('affaire_id', '=', vals['affaire_id'])])
                numero = existing_count + 1
                vals['name'] = f"{affaire.name}/SA{str(numero).zfill(3)}"
        
        # Assigner automatiquement le chargé d'affaire comme inspecteur par défaut
        sous_affaire = super().create(vals)
        
        # Créer l'entrée pour le chargé d'affaire principal
        if sous_affaire.charge_affaire_principal:
            self.env['kes_inspections.sous_affaire_inspecteur'].create({
                'sous_affaire_id': sous_affaire.id,
                'inspecteur_id': sous_affaire.charge_affaire_principal.id,
                'role': 'site_rapport'
            })
        
        return sous_affaire

    # ─────────────────────────────────────────────────────────────
    # 🔸 ACTIONS
    # ─────────────────────────────────────────────────────────────
    
    def action_voir_inspecteurs(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Inspecteurs - {self.name}',
            'res_model': 'kes_inspections.sous_affaire_inspecteur',
            'view_mode': 'list,form',
            'domain': [('sous_affaire_id', '=', self.id)],
            'context': {'default_sous_affaire_id': self.id}
        }

    def action_voir_etiquettes(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Étiquettes - {self.name}',
            'res_model': 'kes_inspections.etiquette',
            'view_mode': 'list,form',
            'domain': [('sous_affaire_id', '=', self.id)],
            'context': {'default_sous_affaire_id': self.id}
        }

    def action_voir_rapports(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Rapports - {self.name}',
            'res_model': 'kes_inspections.rapport',
            'view_mode': 'list,form',
            'domain': [('sous_affaire_id', '=', self.id)],
            'context': {'default_sous_affaire_id': self.id}
        }
    
    def action_download_bond_commande(self):
        """Télécharge le bond de commande"""
        self.ensure_one()
        if not self.bond_commande_file:
            raise ValidationError("Aucun bond de commande à télécharger.")
        
        return {
            'type': 'ir.actions.act_url',
            'url': f"/web/content/kes_inspections.sous_affaire/{self.id}/bond_commande_file?download=true",
            'target': 'self',
        }
    
    def action_download_pv(self):
        """Télécharge le PV"""
        self.ensure_one()
        if not self.pv_file:
            raise ValidationError("Aucun PV à télécharger.")
        
        return {
            'type': 'ir.actions.act_url',
            'url': f"/web/content/kes_inspections.sous_affaire/{self.id}/pv_file?download=true",
            'target': 'self',
        }
    
    def action_download_enquete(self):
        """Télécharge l'enquête de satisfaction"""
        self.ensure_one()
        if not self.enquete_satisfaction_file:
            raise ValidationError("Aucune enquête de satisfaction à télécharger.")
        
        return {
            'type': 'ir.actions.act_url',
            'url': f"/web/content/kes_inspections.sous_affaire/{self.id}/enquete_satisfaction_file?download=true",
            'target': 'self',
        }
    
    # 🔹 CORRECTION : Ajouter le champ client_id manquant
    client_id = fields.Many2one(
        'res.partner',
        string='Client',
        related='affaire_id.client_id',
        readonly=True,
        store=True
    )

    def action_generer_toutes_etiquettes(self):
        """Génère les étiquettes pour tous les produits configurés"""
        self.ensure_one()
        
        if not self.produit_etiquette_ids:
            raise ValidationError("Aucun produit configuré pour la génération d'étiquettes.")
        
        etiquettes_crees = 0
        for produit_line in self.produit_etiquette_ids:
            if produit_line.nombre_etiquettes > 0:
                try:
                    etiquettes_crees += produit_line.generer_etiquettes()
                except Exception as e:
                    raise ValidationError(f"Erreur lors de la génération pour {produit_line.product_id.name}: {str(e)}")
        
        if etiquettes_crees > 0:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Étiquettes générées',
                    'message': f'{etiquettes_crees} étiquette(s) générée(s) avec succès',
                    'sticky': False,
                }
            }
        else:
            raise ValidationError("Aucune étiquette générée. Vérifiez les quantités configurées.")

    def action_download_all_etiquettes(self):
        """Télécharge toutes les étiquettes en fichier ZIP"""
        self.ensure_one()
        if not self.etiquette_ids:
            raise ValidationError("Aucune étiquette à télécharger.")
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Fonctionnalité à venir',
                'message': 'Le téléchargement ZIP sera disponible prochainement',
                'sticky': False,
            }
        }
    

class KesBondCommande(models.Model):
    _name = 'kes_inspections.bond_commande'
    _description = 'Bond de commande'

    sous_affaire_id = fields.Many2one(
        'kes_inspections.sous_affaire',
        string='Sous-affaire',
        required=True,
        ondelete='cascade'
    )

    bond_commande_filename = fields.Char(string='Nom du fichier', required=True)
    bond_commande_file = fields.Binary(string='Fichier bond de commande', required=True)
    date_upload = fields.Datetime(string='Date d\'envoi', default=fields.Datetime.now)

    def action_download_bond_commande(self):
        """Télécharger le bond de commande"""
        self.ensure_one()
        if not self.bond_commande_file:
            raise ValidationError("Aucun fichier à télécharger.")
        return {
            'type': 'ir.actions.act_url',
            'url': f"/web/content/{self._name}/{self.id}/bond_commande_file?download=true",
            'target': 'self',
        }


class KesPV(models.Model):
    _name = 'kes_inspections.pv'
    _description = 'Procès-verbal'

    sous_affaire_id = fields.Many2one(
        'kes_inspections.sous_affaire',
        string='Sous-affaire',
        required=True,
        ondelete='cascade'
    )

    pv_filename = fields.Char(string='Nom du fichier', required=True)
    pv_file = fields.Binary(string='Fichier PV', required=True)
    date_upload = fields.Datetime(string='Date d\'envoi', default=fields.Datetime.now)

    def action_download_pv(self):
        """Télécharger le PV"""
        self.ensure_one()
        if not self.pv_file:
            raise ValidationError("Aucun fichier à télécharger.")
        return {
            'type': 'ir.actions.act_url',
            'url': f"/web/content/{self._name}/{self.id}/pv_file?download=true",
            'target': 'self',
        }


class KesEnqueteSatisfaction(models.Model):
    _name = 'kes_inspections.enquete_satisfaction'
    _description = 'Enquête de satisfaction'

    sous_affaire_id = fields.Many2one(
        'kes_inspections.sous_affaire',
        string='Sous-affaire',
        required=True,
        ondelete='cascade'
    )

    enquete_satisfaction_filename = fields.Char(string='Nom du fichier', required=True)
    enquete_satisfaction_file = fields.Binary(string='Fichier enquête satisfaction', required=True)
    date_upload = fields.Datetime(string='Date d\'envoi', default=fields.Datetime.now)

    def action_download_enquete(self):
        """Télécharger le fichier d'enquête"""
        self.ensure_one()
        if not self.enquete_satisfaction_file:
            raise ValidationError("Aucun fichier à télécharger.")
        return {
            'type': 'ir.actions.act_url',
            'url': f"/web/content/{self._name}/{self.id}/enquete_satisfaction_file?download=true",
            'target': 'self',
        }
