package com.comic2pdf.desktop;

/**
 * Compat stub — délègue vers {@link com.comic2pdf.desktop.model.DupRow}.
 * À supprimer après migration complète des imports.
 *
 * @deprecated Utiliser {@link com.comic2pdf.desktop.model.DupRow}.
 */
@Deprecated(since = "2026-03", forRemoval = true)
public class DupRow extends com.comic2pdf.desktop.model.DupRow {

    /**
     * @param jobKey        Clé unique du job doublon.
     * @param incomingFile  Nom du fichier entrant.
     * @param existingState État du job existant.
     */
    public DupRow(String jobKey, String incomingFile, String existingState) {
        super(jobKey, incomingFile, existingState);
    }
}
