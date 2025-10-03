from odoo import models, fields, api
import base64
import os

class LabelTemplate(models.Model):
    _name = 'label.template'
    _description = 'Modèle d\'étiquette'
    _order = 'sequence, name'
    
    name = fields.Char('Nom du modèle', required=True)
    sequence = fields.Integer('Séquence', default=10)
    template_image = fields.Image('Image du modèle', required=True)
    active = fields.Boolean('Actif', default=True)
    
    # Positions pour le QR code (en pixels depuis le coin supérieur gauche)
    qr_position_x = fields.Integer('Position QR X', default=50)
    qr_position_y = fields.Integer('Position QR Y', default=50)
    qr_size = fields.Integer('Taille QR', default=100)
    
    # Positions pour le texte client
    client_number_x = fields.Integer('Position Numéro Client X', default=200)
    client_number_y = fields.Integer('Position Numéro Client Y', default=50)
    client_name_x = fields.Integer('Position Nom Client X', default=200)
    client_name_y = fields.Integer('Position Nom Client Y', default=80)
    
    # Style du texte
    font_size = fields.Integer('Taille Police', default=12)
    font_color = fields.Char('Couleur Police', default='#000000')
    
    # Type de produit/service associé
    product_ids = fields.Many2many('product.product', string='Produits')
    
    @api.model
    def get_template_for_product(self, product_id):
        """Retourne le modèle approprié pour un produit donné"""
        product = self.env['product.product'].browse(product_id)
        if product.categ_id:
            template = self.search([
                ('product_ids', 'in', [product.id]),
                ('active', '=', True)
            ], limit=1)
            if template:
                return template
        # Modèle par défaut
        return self.search([('active', '=', True)], limit=1)
    
    @api.model
    def _load_image_from_module(self, image_path):
        """Charge une image depuis le module et la convertit en base64"""
        try:
            module_path = os.path.dirname(os.path.dirname(__file__))
            full_path = os.path.join(module_path, image_path)
            
            if os.path.exists(full_path):
                with open(full_path, 'rb') as image_file:
                    return base64.b64encode(image_file.read())
            return False
        except Exception as e:
            return False