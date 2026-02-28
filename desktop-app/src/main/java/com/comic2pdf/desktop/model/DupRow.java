package com.comic2pdf.desktop.model;

import javafx.beans.property.SimpleStringProperty;
import javafx.beans.property.StringProperty;

/**
 * Modèle JavaFX représentant une ligne de doublon en attente de décision.
 *
 * <p>Propriétés observables : {@code jobKey}, {@code incomingFile}, {@code existingState}.</p>
 */
public class DupRow {

    private final StringProperty jobKey = new SimpleStringProperty();
    private final StringProperty incomingFile = new SimpleStringProperty();
    private final StringProperty existingState = new SimpleStringProperty();

    /**
     * Construit un {@code DupRow} avec tous les champs.
     *
     * @param jobKey        Clé unique du job doublon.
     * @param incomingFile  Nom du fichier entrant.
     * @param existingState État du job existant.
     */
    public DupRow(String jobKey, String incomingFile, String existingState) {
        this.jobKey.set(jobKey);
        this.incomingFile.set(incomingFile);
        this.existingState.set(existingState);
    }

    /** @return Clé du job doublon. */
    public String getJobKey() { return jobKey.get(); }

    /** @return Propriété JavaFX jobKey. */
    public StringProperty jobKeyProperty() { return jobKey; }

    /** @return Nom du fichier entrant. */
    public String getIncomingFile() { return incomingFile.get(); }

    /** @return Propriété JavaFX incomingFile. */
    public StringProperty incomingFileProperty() { return incomingFile; }

    /** @return État du job existant. */
    public String getExistingState() { return existingState.get(); }

    /** @return Propriété JavaFX existingState. */
    public StringProperty existingStateProperty() { return existingState; }
}

