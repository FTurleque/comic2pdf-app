package com.comic2pdf.desktop.duplicates;

import com.comic2pdf.desktop.model.DupRow;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.io.IOException;
import java.nio.file.Path;
import java.util.List;

/**
 * Compat stub — délègue vers {@link com.comic2pdf.desktop.service.DuplicateService}.
 * À supprimer après migration complète des imports.
 *
 * @deprecated Utiliser {@link com.comic2pdf.desktop.service.DuplicateService}.
 */
@Deprecated(since = "2026-03", forRemoval = true)
public class DuplicateService {

    private final com.comic2pdf.desktop.service.DuplicateService delegate;

    /** Construit un stub avec un ObjectMapper par défaut. */
    public DuplicateService() {
        this.delegate = new com.comic2pdf.desktop.service.DuplicateService();
    }

    /** Construit un stub avec un ObjectMapper fourni. */
    public DuplicateService(ObjectMapper mapper) {
        this.delegate = new com.comic2pdf.desktop.service.DuplicateService(mapper);
    }

    /**
     * Délègue vers {@link com.comic2pdf.desktop.service.DuplicateService#listDuplicates(Path)}.
     *
     * @param dataDir Racine du répertoire data/.
     * @return Liste de DupRow.
     * @throws IOException En cas d'erreur de lecture.
     */
    public List<DupRow> listDuplicates(Path dataDir) throws IOException {
        return delegate.listDuplicates(dataDir);
    }

    /**
     * Délègue vers
     * {@link com.comic2pdf.desktop.service.DuplicateService#writeDecision(Path, String,
     *         com.comic2pdf.desktop.model.DuplicateDecision)}.
     *
     * @param dataDir  Racine du répertoire data/.
     * @param jobKey   Clé du job doublon.
     * @param decision Décision prise.
     * @return Chemin du fichier decision.json écrit.
     * @throws IOException En cas d'erreur d'écriture.
     */
    public Path writeDecision(Path dataDir, String jobKey, DuplicateDecision decision)
            throws IOException {
        // Conversion de l'enum deprecated vers la nouvelle
        com.comic2pdf.desktop.model.DuplicateDecision newDecision =
                com.comic2pdf.desktop.model.DuplicateDecision.valueOf(decision.name());
        return delegate.writeDecision(dataDir, jobKey, newDecision);
    }
}
