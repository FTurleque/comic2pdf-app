package com.comic2pdf.desktop;

/**
 * Compat stub — délègue vers {@link com.comic2pdf.desktop.model.JobRow}.
 * À supprimer après migration complète des imports.
 *
 * @deprecated Utiliser {@link com.comic2pdf.desktop.model.JobRow}.
 */
@Deprecated(since = "2026-03", forRemoval = true)
public class JobRow extends com.comic2pdf.desktop.model.JobRow {

    /**
     * @param jobKey    Clé unique du job.
     * @param state     État global.
     * @param stage     Étape en cours.
     * @param attempt   Numéro de tentative.
     * @param updatedAt Horodatage ISO.
     * @param inputName Nom du fichier d'entrée.
     */
    public JobRow(String jobKey, String state, String stage,
                  String attempt, String updatedAt, String inputName) {
        super(jobKey, state, stage, attempt, updatedAt, inputName);
    }
}
