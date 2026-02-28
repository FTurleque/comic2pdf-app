package com.fturleque.comic2pdf.desktop;

import javafx.beans.property.SimpleStringProperty;
import javafx.beans.property.StringProperty;

/**
 * Modèle JavaFX représentant une ligne de la vue "Jobs" (état d'un job de l'orchestrateur).
 *
 * <p>Champs : jobKey, state, stage, attempt, updatedAt, inputName.</p>
 */
public class JobRow {

    private final StringProperty jobKey = new SimpleStringProperty();
    private final StringProperty state = new SimpleStringProperty();
    private final StringProperty stage = new SimpleStringProperty();
    private final StringProperty attempt = new SimpleStringProperty();
    private final StringProperty updatedAt = new SimpleStringProperty();
    private final StringProperty inputName = new SimpleStringProperty();

    /**
     * Construit un {@code JobRow} avec tous les champs.
     *
     * @param jobKey    Clé unique du job.
     * @param state     État global (DONE, ERROR, PREP_RUNNING, etc.).
     * @param stage     Étape en cours dans in_flight (peut être vide).
     * @param attempt   Numéro de tentative courante.
     * @param updatedAt Horodatage ISO de dernière mise à jour.
     * @param inputName Nom du fichier d'entrée.
     */
    public JobRow(String jobKey, String state, String stage,
                  String attempt, String updatedAt, String inputName) {
        this.jobKey.set(jobKey);
        this.state.set(state);
        this.stage.set(stage);
        this.attempt.set(attempt);
        this.updatedAt.set(updatedAt);
        this.inputName.set(inputName);
    }

    /** @return jobKey du job. */
    public String getJobKey() { return jobKey.get(); }
    /** @return Propriété JavaFX jobKey. */
    public StringProperty jobKeyProperty() { return jobKey; }

    /** @return État global du job. */
    public String getState() { return state.get(); }
    /** @return Propriété JavaFX state. */
    public StringProperty stateProperty() { return state; }

    /** @return Étape en cours. */
    public String getStage() { return stage.get(); }
    /** @return Propriété JavaFX stage. */
    public StringProperty stageProperty() { return stage; }

    /** @return Numéro de tentative sous forme de chaîne. */
    public String getAttempt() { return attempt.get(); }
    /** @return Propriété JavaFX attempt. */
    public StringProperty attemptProperty() { return attempt; }

    /** @return Horodatage de la dernière mise à jour. */
    public String getUpdatedAt() { return updatedAt.get(); }
    /** @return Propriété JavaFX updatedAt. */
    public StringProperty updatedAtProperty() { return updatedAt; }

    /** @return Nom du fichier source. */
    public String getInputName() { return inputName.get(); }
    /** @return Propriété JavaFX inputName. */
    public StringProperty inputNameProperty() { return inputName; }

    /**
     * Met à jour tous les champs depuis un autre {@code JobRow}.
     * Permet le refresh périodique sans recréer les lignes.
     *
     * @param other Nouvelle version du même job.
     */
    public void updateFrom(JobRow other) {
        this.state.set(other.getState());
        this.stage.set(other.getStage());
        this.attempt.set(other.getAttempt());
        this.updatedAt.set(other.getUpdatedAt());
        this.inputName.set(other.getInputName());
    }
}

