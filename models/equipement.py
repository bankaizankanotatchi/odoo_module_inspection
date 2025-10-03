# models/equipement.py - VERSION COMPLÈTE
from odoo import models, fields, api
from odoo.exceptions import ValidationError
import secrets
import string
import base64
from io import BytesIO
import zipfile


class InspectionEquipement(models.Model):
    _name = 'kes_inspections.equipement'
    _description = 'Équipement à inspecter'
    _order = 'sequence, name'
    
    name = fields.Char(string='Nom équipement', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    affaire_id = fields.Many2one('kes_inspections.affaire', string='Affaire', required=True, ondelete='cascade')
    
    # 🔹 Types d’équipements basés sur les 8 types d’étiquettes à générer
    type_equipement = fields.Selection([
        ('inspection_electrique', 'Inspection Électrique'),
        ('inspection_thermographie', 'Inspection Thermographique'),
        ('identification_local', 'Identification du Local Électrique'),
        ('ascenseur', 'Ascenseur'),
        ('verification_periodique', 'Vérification Périodique des Équipements'),
        ('verification_extincteur', 'Vérification des Extincteurs'),
        ('arc_flash', 'Arc Flash'),
        ('plaque_identification', 'Plaque d’Identification Extérieure'),
    ], string='Type d’équipement', required=True, default='inspection_electrique')
    
    # 🔹 Codes automatiques associés
    _CODE_PREFIXES = {
        'inspection_electrique': 'IEL',
        'inspection_thermographie': 'ITH',
        'identification_local': 'LOC',
        'ascenseur': 'ASC',
        'verification_periodique': 'VPE',
        'verification_extincteur': 'VEX',
        'arc_flash': 'ARC',
        'plaque_identification': 'PID',
    }
    
    # Code équipement de base (généré automatiquement)
    code_equipement = fields.Char(string='Code équipement', compute='_compute_code_equipement', store=True, readonly=True)
    
    # Gestion des étiquettes uniques
    etiquette_ids = fields.One2many('kes_inspections.etiquette', 'equipement_id', string='Étiquettes générées')
    nombre_etiquettes = fields.Integer(string='Nombre d étiquettes à générer', default=1, required=True)
    etiquettes_generes = fields.Boolean(string='Étiquettes générées', compute='_compute_etiquettes_generes', store=True)
    total_etiquettes_generees = fields.Integer(string='Étiquettes générées', compute='_compute_total_etiquettes')
    
    localisation = fields.Char(string='Localisation précise')
    description = fields.Text(string='Description')
    
    # Statut
    state = fields.Selection([
        ('a_inspecter', 'À inspecter'),
        ('en_cours', 'En cours dinspection'),
        ('inspecte', 'Inspecté'),
        ('conforme', 'Conforme'),
        ('non_conforme', 'Non conforme'),
    ], string='Statut', default='a_inspecter', tracking=True)
    
    @api.depends('type_equipement', 'affaire_id', 'affaire_id.equipement_ids')
    def _compute_code_equipement(self):
        """Génère le code équipement basé sur le type et le compteur"""
        for equipement in self:
            if equipement.type_equipement and equipement.affaire_id:
                prefix = self._CODE_PREFIXES.get(equipement.type_equipement, 'EQU')
                
                # Compter les équipements du même type dans cette affaire
                same_type_count = self.search_count([
                    ('affaire_id', '=', equipement.affaire_id.id),
                    ('type_equipement', '=', equipement.type_equipement),
                    ('id', '!=', equipement.id)  # Exclure l'équipement actuel
                ])
                
                numero = same_type_count + 1
                equipement.code_equipement = f"{equipement.affaire_id.name}/{prefix}{str(numero).zfill(3)}"
            else:
                equipement.code_equipement = "CODE_PENDING"
    
    @api.depends('etiquette_ids')
    def _compute_etiquettes_generes(self):
        """Détermine si des étiquettes ont été générées"""
        for equipement in self:
            equipement.etiquettes_generes = len(equipement.etiquette_ids) > 0
    
    @api.depends('etiquette_ids')
    def _compute_total_etiquettes(self):
        """Calcule le nombre total d'étiquettes générées"""
        for equipement in self:
            equipement.total_etiquettes_generees = len(equipement.etiquette_ids)
    
    @api.onchange('type_equipement')
    def _onchange_type_equipement(self):
        """Met à jour le code quand le type change"""
        self._compute_code_equipement()
    
    def action_generer_etiquettes(self):
        """Génère des étiquettes uniques pour l'équipement"""
        self.ensure_one()
        
        # Validation
        if self.nombre_etiquettes <= 0:
            raise ValidationError("Le nombre d'étiquettes doit être supérieur à 0")
        
        # Supprimer les anciennes étiquettes
        self.etiquette_ids.unlink()
        
        # Générer de nouvelles étiquettes uniques
        codes_generes = set()
        for i in range(self.nombre_etiquettes):
            # Générer un code unique (éviter les doublons)
            for attempt in range(10):  # 10 tentatives max
                code_unique = self._generer_code_etiquette_unique(i + 1)
                if code_unique not in codes_generes:
                    codes_generes.add(code_unique)
                    break
            else:
                raise ValidationError("Impossible de générer un code d'étiquette unique")
            
            # Créer l'étiquette
            self.env['kes_inspections.etiquette'].create({
                'equipement_id': self.id,
                'code_etiquette': code_unique,
                'numero_etiquette': i + 1,
                'date_generation': fields.Date.today(),
            })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Étiquettes générées',
                'message': f'{self.nombre_etiquettes} étiquette(s) unique(s) générée(s) pour {self.name}',
                'sticky': False,
            }
        }
    
    def _generer_code_etiquette_unique(self, numero):
        """Génère un code d'étiquette unique avec suffixe aléatoire"""
        # Code base + suffixe aléatoire de 4 caractères
        suffixe = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4))
        return f"{self.code_equipement}/ET{str(numero).zfill(2)}_{suffixe}"
    
    def action_voir_etiquettes(self):
        """Ouvre la vue des étiquettes générées"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Étiquettes - {self.name}',
            'res_model': 'kes_inspections.etiquette',
            'view_mode': 'list,form',
            'domain': [('equipement_id', '=', self.id)],
            'context': {'default_equipement_id': self.id}
        }
    
    def action_generate_zip_etiquettes(self):
        """Génère un ZIP avec toutes les étiquettes sélectionnées"""
        if not self:
            raise ValidationError("Aucune étiquette sélectionnée.")
        
        zip_buffer = BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for etiquette in self:
                try:
                    # Générer l'image
                    etiquette_image = etiquette.generate_etiquette_image()
                    
                    # Convertir en bytes
                    img_buffer = BytesIO()
                    etiquette_image.save(img_buffer, format='PNG')
                    img_buffer.seek(0)
                    
                    # Ajouter au ZIP
                    filename = f"etiquette_{etiquette.code_etiquette}.png"
                    zip_file.writestr(filename, img_buffer.getvalue())
                    
                except Exception as e:
                    raise ValidationError(f"Erreur avec l'étiquette {etiquette.code_etiquette}: {str(e)}")
        
        zip_buffer.seek(0)
        zip_data = base64.b64encode(zip_buffer.getvalue())
        
        # Créer attachment pour téléchargement
        attachment = self.env['ir.attachment'].create({
            'name': f'etiquettes_{fields.Datetime.now().strftime("%Y%m%d_%H%M%S")}.zip',
            'type': 'binary',
            'datas': zip_data,
            'res_model': 'kes_inspections.etiquette',
            'mimetype': 'application/zip'
        })
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }