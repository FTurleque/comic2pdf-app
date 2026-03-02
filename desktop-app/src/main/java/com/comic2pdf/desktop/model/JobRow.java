package com.comic2pdf.desktop.model;

import javafx.beans.property.SimpleStringProperty;
import javafx.beans.property.StringProperty;

/**
 * Modèle JavaFX représentant une ligne de la vue "Jobs".
 *
 * <p>Champs : jobKey, state, stage, attempt, updatedAt, inputName,
 * outPdf, errorMessage, startedAt, endedAt.</p>
 */
public class JobRow {

    private final StringProperty jobKey       = new SimpleStringProperty();
    private final StringProperty state        = new SimpleStringProperty();
    private final StringProperty stage        = new SimpleStringProperty();
    private final StringProperty attempt      = new SimpleStringProperty();
    private final StringProperty updatedAt    = new SimpleStringProperty();
    private final StringProperty inputName    = new SimpleStringProperty();
    private final StringProperty outPdf       = new SimpleStringProperty();
    private final StringProperty errorMessage = new SimpleStringProperty();
    private final StringProperty startedAt    = new SimpleStringProperty();
    private final StringProperty endedAt      = new SimpleStringProperty();

    /**
     * Constructeur minimal — rétrocompatibilité ascendante.
     *
     * @param jobKey    Clé unique du job.
     * @param state     État global.
     * @param stage     Étape en cours.
     * @param attempt   Numéro de tentative.
     * @param updatedAt Horodatage ISO de dernière mise à jour.
     * @param inputName Nom du fichier d'entrée.
     */
    public JobRow(String jobKey, String state, String stage,
                  String attempt, String updatedAt, String inputName) {
        this(jobKey, state, stage, attempt, updatedAt, inputName, "", "");
    }

    /**
     * Constructeur enrichi sans startedAt/endedAt — rétrocompatibilité.
     *
     * @param jobKey       Clé unique du job.
     * @param state        État global.
     * @param stage        Étape en cours.
     * @param attempt      Numéro de tentative.
     * @param updatedAt    Horodatage ISO de dernière mise à jour.
     * @param inputName    Nom du fichier d'entrée.
     * @param outPdf       Chemin PDF de sortie (vide si absent).
     * @param errorMessage Message d'erreur (vide si absent).
     */
    public JobRow(String jobKey, String state, String stage,
                  String attempt, String updatedAt, String inputName,
                  String outPdf, String errorMessage) {
        this(jobKey, state, stage, attempt, updatedAt, inputName,
             outPdf, errorMessage, "", "");
    }

    /**
     * Constructeur complet avec toutes les propriétés temporelles.
     *
     * @param jobKey       Clé unique du job.
     * @param state        État global (DONE, ERROR, PREP_RUNNING, etc.).
     * @param stage        Étape en cours (peut être vide).
     * @param attempt      Numéro de tentative courante.
     * @param updatedAt    Horodatage ISO de dernière mise à jour.
     * @param inputName    Nom du fichier d'entrée.
     * @param outPdf       Chemin PDF de sortie (vide si absent).
     * @param errorMessage Message d'erreur (vide si absent).
     * @param startedAt    Horodatage ISO de démarrage (vide si absent).
     * @param endedAt      Horodatage ISO de fin (vide si absent).
     */
    public JobRow(String jobKey, String state, String stage,
                  String attempt, String updatedAt, String inputName,
                  String outPdf, String errorMessage,
                  String startedAt, String endedAt) {
        this.jobKey.set(jobKey);
        this.state.set(state);
        this.stage.set(stage);
        this.attempt.set(attempt);
        this.updatedAt.set(updatedAt);
        this.inputName.set(inputName);
        this.outPdf.set(outPdf != null ? outPdf : "");
        this.errorMessage.set(errorMessage != null ? errorMessage : "");
        this.startedAt.set(startedAt != null ? startedAt : "");
        this.endedAt.set(endedAt != null ? endedAt : "");
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

    /** @return Chemin du PDF de sortie, ou chaîne vide si absent. */
    public String getOutPdf() { return outPdf.get(); }
    /** @return Propriété JavaFX outPdf. */
    public StringProperty outPdfProperty() { return outPdf; }

    /** @return Message d'erreur, ou chaîne vide si pas en erreur. */
    public String getErrorMessage() { return errorMessage.get(); }
    /** @return Propriété JavaFX errorMessage. */
    public StringProperty errorMessageProperty() { return errorMessage; }

    /** @return Horodatage ISO de démarrage, chaîne vide si absent. */
    public String getStartedAt() { return startedAt.get(); }
    /** @return Propriété JavaFX startedAt. */
    public StringProperty startedAtProperty() { return startedAt; }

    /** @return Horodatage ISO de fin, chaîne vide si absent. */
    public String getEndedAt() { return endedAt.get(); }
    /** @return Propriété JavaFX endedAt. */
    public StringProperty endedAtProperty() { return endedAt; }

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
        this.outPdf.set(other.getOutPdf());
        this.errorMessage.set(other.getErrorMessage());
        this.startedAt.set(other.getStartedAt());
        this.endedAt.set(other.getEndedAt());
    }
}

