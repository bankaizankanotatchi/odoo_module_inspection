# __init__.py
from . import models

# Hook pour charger les images automatiquement - VERSION CORRIGÉE
def post_init_hook(env):
    """Charge les images des templates après installation - Version Odoo 17+"""
    import base64
    import os
    
    module_path = os.path.dirname(os.path.abspath(__file__))
    
    # Mapping templates -> images
    templates_data = [
        ('label_template_iec', 'iec.png'),
        ('label_template_ienc', 'ienc.png'),
        ('label_template_le', 'le.png'),
        ('label_template_vcie', 'vcie.png'),
        ('label_template_vgpa', 'vgpa.png'),
        ('label_template_vgpeis', 'vgpeis.png'),
        ('label_template_vpge', 'vpge.png'),
        ('label_template_vti', 'vti.png'),
    ]
    
    for xml_id, image_name in templates_data:
        try:
            template = env.ref(f'kes_inspections.{xml_id}', raise_if_not_found=False)
            if template:
                image_path = os.path.join(module_path, 'static', 'description', 'templates', image_name)
                if os.path.exists(image_path):
                    with open(image_path, 'rb') as f:
                        image_data = base64.b64encode(f.read())
                        template.write({'template_image': image_data})
                    print(f"✅ Image chargée: {xml_id}")
                else:
                    print(f"⚠️ Image non trouvée: {image_path}")
            else:
                print(f"⚠️ Template non trouvé: {xml_id}")
        except Exception as e:
            print(f"❌ Erreur pour {xml_id}: {str(e)}")