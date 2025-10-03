/** @odoo-module **/

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";

class LabelGeneratorComponent extends Component {
    static template = "label_qr_generator.LabelGenerator";

    setup() {
        super.setup();
        this.state = {
            isGenerating: false,
            progress: 0
        };
    }

    async onGenerateLabels(ev) {
        try {
            this.state.isGenerating = true;
            this.render();

            // Appeler la méthode Python
            const result = await this.env.services.rpc("/web/dataset/call_kw", {
                model: 'label.generator',
                method: 'action_generate_labels',
                args: [this.props.record.resId],
                kwargs: {}
            });

            this.state.isGenerating = false;
            this.render();

            if (result && result.type === 'ir.actions.act_window') {
                this.env.services.action.doAction(result);
            }
        } catch (error) {
            this.state.isGenerating = false;
            this.render();
            console.error('Erreur lors de la génération:', error);
        }
    }
}

registry.category("view_widgets").add("label_generator", LabelGeneratorComponent);