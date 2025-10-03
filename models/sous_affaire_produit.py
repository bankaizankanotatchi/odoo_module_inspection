from odoo import models, fields, api
from odoo.exceptions import ValidationError
import secrets
import string

class SousAffaireProduit(models.Model):
    _name = 'kes_inspections.sous_affaire_produit'
    _description = 'Produit pour génération d\'étiquettes dans sous-affaire'
    
    sous_affaire_id = fields.Many2one(
        'kes_inspections.sous_affaire',
        string='Sous-affaire',
        required=True,
        ondelete='cascade'
    )
    
    product_id = fields.Many2one(
        'product.product',
        string='Produit',
        required=True,
        domain="[('id', 'in', product_domain_ids)]"
    )
    
    product_domain_ids = fields.Many2many(
        'product.product',
        string='Produits disponibles',
        compute='_compute_product_domain'
    )
    
    nombre_etiquettes = fields.Integer(
        string='Nombre d\'étiquettes à générer',
        default=1,
        required=True
    )
    
    etiquettes_generes = fields.Boolean(
        string='Étiquettes générées',
        compute='_compute_etiquettes_generes'
    )
    
    etiquette_ids = fields.One2many(
        'kes_inspections.etiquette',
        'sous_affaire_produit_id',
        string='Étiquettes générées'
    )
    
    etiquette_count = fields.Integer(
        string='Étiquettes générées',
        compute='_compute_etiquette_count'
    )
    

    @api.depends('sous_affaire_id', 'sous_affaire_id.type_intervention_ids')
    def _compute_product_domain(self):
        """Limite le choix aux produits de la commande de vente"""
        for record in self:
            if record.sous_affaire_id and record.sous_affaire_id.type_intervention_ids:
                record.product_domain_ids = [(6, 0, record.sous_affaire_id.type_intervention_ids.ids)]
            else:
                record.product_domain_ids = [(5, 0, 0)]

    @api.depends('etiquette_ids')
    def _compute_etiquettes_generes(self):
        for record in self:
            record.etiquettes_generes = len(record.etiquette_ids) > 0

    @api.depends('etiquette_ids')
    def _compute_etiquette_count(self):
        for record in self:
            record.etiquette_count = len(record.etiquette_ids)

    def generer_etiquettes(self):
        """Génère les étiquettes pour ce produit"""
        self.ensure_one()
        
        if self.nombre_etiquettes <= 0:
            raise ValidationError("Le nombre d'étiquettes doit être supérieur à 0")
        
        # Supprimer les anciennes étiquettes
        self.etiquette_ids.unlink()
        
        # Déterminer le type d'équipement basé sur le produit
        type_equipement = self._get_equipement_type_from_product()
        
        # Créer un équipement virtuel pour cette génération
        equipement_vals = {
            'name': f"{self.product_id.name} - {self.sous_affaire_id.name}",
            'affaire_id': self.sous_affaire_id.affaire_id.id,
            'type_equipement': type_equipement,
            'nombre_etiquettes': self.nombre_etiquettes,
        }
        
        equipement = self.env['kes_inspections.equipement'].create(equipement_vals)
        
        # Générer les étiquettes
        codes_generes = set()
        for i in range(self.nombre_etiquettes):
            for attempt in range(10):  # 10 tentatives max
                code_unique = self._generer_code_etiquette_unique(i + 1, equipement)
                if code_unique not in codes_generes:
                    codes_generes.add(code_unique)
                    break
            else:
                raise ValidationError("Impossible de générer un code d'étiquette unique")
            
            # Créer l'étiquette
            etiquette_vals = {
                'sous_affaire_produit_id': self.id,
                'sous_affaire_id': self.sous_affaire_id.id,
                'equipement_id': equipement.id,
                'code_etiquette': code_unique,
                'numero_etiquette': i + 1,
                'date_generation': fields.Date.today(),
            }
            
            self.env['kes_inspections.etiquette'].create(etiquette_vals)
        
        return self.nombre_etiquettes

    def _get_equipement_type_from_product(self):
        """Détermine le type d'équipement basé sur le nom du produit"""
        product_name_lower = self.product_id.name.lower()
        
        if 'electrique' in product_name_lower:
            return 'inspection_electrique'
        elif 'thermographie' in product_name_lower or 'thermographique' in product_name_lower:
            return 'inspection_thermographie'
        elif 'ascenseur' in product_name_lower:
            return 'ascenseur'
        elif 'extincteur' in product_name_lower:
            return 'verification_extincteur'
        elif 'local' in product_name_lower:
            return 'identification_local'
        elif 'periodique' in product_name_lower:
            return 'verification_periodique'
        elif 'arc' in product_name_lower and 'flash' in product_name_lower:
            return 'arc_flash'
        elif 'plaque' in product_name_lower:
            return 'plaque_identification'
        else:
            return 'inspection_electrique'  # Type par défaut

    def _generer_code_etiquette_unique(self, numero, equipement):
        """Génère un code d'étiquette unique"""
        prefix_map = {
            'inspection_electrique': 'IEL',
            'inspection_thermographie': 'ITH',
            'identification_local': 'LOC',
            'ascenseur': 'ASC',
            'verification_periodique': 'VPE',
            'verification_extincteur': 'VEX',
            'arc_flash': 'ARC',
            'plaque_identification': 'PID',
        }
        
        prefix = prefix_map.get(equipement.type_equipement, 'EQU')
        suffixe = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4))
        
        return f"{self.sous_affaire_id.name}/{prefix}-{self.product_id.default_code or 'PROD'}-{str(numero).zfill(3)}_{suffixe}"

    def action_voir_etiquettes(self):
        """Ouvre la vue des étiquettes générées pour ce produit"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Étiquettes - {self.product_id.name}',
            'res_model': 'kes_inspections.etiquette',
            'view_mode': 'list,form',
            'domain': [('sous_affaire_produit_id', '=', self.id)],
            'context': {'default_sous_affaire_produit_id': self.id}
        }

    def action_generer_etiquettes(self):
        """Génère les étiquettes pour ce produit spécifique"""
        self.ensure_one()
        count = self.generer_etiquettes()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Étiquettes générées',
                'message': f'{count} étiquette(s) générée(s) pour {self.product_id.name}',
                'sticky': False,
            }
        }