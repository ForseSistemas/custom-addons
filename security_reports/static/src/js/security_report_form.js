/** @odoo-module **/

import { registry } from "@web/core/registry";
import { formView } from "@web/views/form/form_view";
import { FormController } from "@web/views/form/form_controller";

// Botón del reporte -> prefijo de los campos donde se guarda la ubicación
const GPS_BUTTONS = {
    action_iniciar_trabajo: "gps_inicio",
    action_finalizar: "gps_fin",
};

/**
 * Pide la ubicación al navegador. Si el técnico la niega, si el navegador no
 * la ofrece (por ejemplo, sin HTTPS) o si tarda demasiado, devuelve null y el
 * flujo continúa sin ubicación.
 */
function getPosition() {
    return new Promise((resolve) => {
        if (!navigator.geolocation) {
            resolve(null);
            return;
        }
        navigator.geolocation.getCurrentPosition(
            (position) => resolve(position.coords),
            () => resolve(null),
            { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 }
        );
    });
}

export class SecurityReportFormController extends FormController {
    async beforeExecuteActionButton(clickParams) {
        const prefix = GPS_BUTTONS[clickParams.name];
        if (prefix) {
            try {
                const coords = await getPosition();
                if (coords) {
                    await this.model.root.update({
                        [`${prefix}_lat`]: coords.latitude,
                        [`${prefix}_lng`]: coords.longitude,
                    });
                }
            } catch (error) {
                // La ubicación es un extra: nunca debe impedir el trabajo.
                console.warn("security_reports: no se pudo registrar la ubicación", error);
            }
        }
        const parent = super.beforeExecuteActionButton;
        return parent ? parent.apply(this, arguments) : undefined;
    }
}

registry.category("views").add("security_report_form", {
    ...formView,
    Controller: SecurityReportFormController,
});
