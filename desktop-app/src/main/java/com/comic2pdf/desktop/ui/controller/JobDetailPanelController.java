package com.comic2pdf.desktop.ui.controller;

import com.comic2pdf.desktop.client.OrchestratorClient;
import com.comic2pdf.desktop.model.JobRow;
import com.comic2pdf.desktop.util.JobDurationUtils;
import javafx.application.Platform;
import javafx.concurrent.Task;
import javafx.fxml.FXML;
import javafx.scene.control.Button;
import javafx.scene.control.Label;
import javafx.scene.control.TextArea;
import javafx.scene.input.Clipboard;
import javafx.scene.input.ClipboardContent;
import javafx.scene.layout.HBox;
import javafx.scene.layout.VBox;

/**
 * Controller du panneau latéral de détail d'un job.
 *
 * <p>Reçoit les données depuis {@link JobsController} via
 * {@link #showDetail(JobRow, String)} et {@link #setLogSections(String, String)}.</p>
 *
 * <p><b>Point d'extensibilité future ({@code /logs} endpoint)</b> : seule la méthode
 * {@link #onReloadDetail()} devra changer pour appeler
 * {@code OrchestratorClient.getJobLogs(id)} si cet endpoint est ajouté.
 * Le reste du panneau (FXML + {@link #setLogSections(String, String)}) reste inchangé.</p>
 */
public class JobDetailPanelController {

    @FXML private Label   emptyLabel;
    @FXML private HBox    loadingBox;
    @FXML private Label   errorLabel;
    @FXML private VBox    detailContent;

    @FXML private Label   detailJobKey;
    @FXML private Label   detailState;
    @FXML private Label   detailStage;
    @FXML private Label   detailAttempt;
    @FXML private Label   detailInputName;
    @FXML private Label   detailStartedAt;
    @FXML private Label   detailEndedAt;
    @FXML private Label   detailDuration;
    @FXML private Label   detailUpdatedAt;
    @FXML private TextArea detailLogsArea;

    @FXML private Button  detailCopyErrorBtn;
    @FXML private Button  detailCopyOutPdfBtn;

    private OrchestratorClient client;
    private String currentJobKey = null;
    private String lastError     = "";
    private String lastOutPdf    = "";

    /**
     * Injecte le client HTTP orchestrateur.
     *
     * @param client Client HTTP.
     */
    public void setClient(OrchestratorClient client) {
        this.client = client;
    }

    /** Initialisation FXML : état initial = vide. */
    @FXML
    public void initialize() {
        showEmpty();
    }

    /** Affiche l'état "aucun job sélectionné". */
    public void showEmpty() {
        setVisibility(true, false, false, false);
        currentJobKey = null;
        lastError     = "";
        lastOutPdf    = "";
    }

    /** Affiche un indicateur de chargement. */
    public void showLoading() {
        setVisibility(false, true, false, false);
    }

    /**
     * Affiche un message d'erreur dans le panneau.
     *
     * @param msg Message à afficher.
     */
    public void showError(String msg) {
        setVisibility(false, false, true, false);
        errorLabel.setText(msg != null ? msg : "Erreur inconnue");
    }

    /**
     * Affiche les détails d'un job.
     * Doit être appelé sur le FX Application Thread.
     *
     * @param row      Ligne de job à afficher.
     * @param duration Durée calculée (format HH:mm:ss ou "N/A").
     */
    public void showDetail(JobRow row, String duration) {
        assert Platform.isFxApplicationThread()
                : "showDetail() doit être appelé sur le FX thread";
        currentJobKey = row.getJobKey();
        detailJobKey.setText(row.getJobKey());
        detailState.setText(row.getState());
        detailStage.setText(row.getStage());
        detailAttempt.setText(row.getAttempt());
        detailInputName.setText(row.getInputName());
        detailStartedAt.setText(row.getStartedAt().isBlank() ? "—" : row.getStartedAt());
        detailEndedAt.setText(row.getEndedAt().isBlank()   ? "—" : row.getEndedAt());
        detailDuration.setText(duration);
        detailUpdatedAt.setText(row.getUpdatedAt());
        setVisibility(false, false, false, true);
    }

    /**
     * Remplit la zone logs avec les sections error et outPdf.
     *
     * <p><b>Conception extensible</b> : quand un endpoint {@code /jobs/{id}/logs} sera
     * disponible, seule la méthode appelante ({@link #onReloadDetail()}) changera.
     * Cette méthode reste inchangée.</p>
     *
     * @param error  Contenu section erreur (vide = section masquée).
     * @param outPdf Chemin PDF de sortie (vide = section masquée).
     */
    public void setLogSections(String error, String outPdf) {
        this.lastError  = error  != null ? error  : "";
        this.lastOutPdf = outPdf != null ? outPdf : "";

        StringBuilder sb = new StringBuilder();
        if (!lastError.isBlank()) {
            sb.append("=== Error ===\n").append(lastError).append("\n\n");
        }
        if (!lastOutPdf.isBlank()) {
            sb.append("=== Output PDF ===\n").append(lastOutPdf).append("\n");
        }
        if (sb.isEmpty()) {
            sb.append("(aucun log disponible)");
        }
        detailLogsArea.setText(sb.toString());
    }

    // -----------------------------------------------------------------------
    // Actions FXML
    // -----------------------------------------------------------------------

    /** Copie le message d'erreur dans le presse-papiers. */
    @FXML
    private void onCopyError() {
        if (!lastError.isBlank()) copyToClipboard(lastError);
    }

    /** Copie le chemin outPdf dans le presse-papiers. */
    @FXML
    private void onCopyOutPdf() {
        if (!lastOutPdf.isBlank()) copyToClipboard(lastOutPdf);
    }

    /**
     * Recharge les détails du job courant depuis l'orchestrateur.
     *
     * <p><b>Point d'extensibilité ({@code /logs} futur)</b> : modifier uniquement
     * cet appel pour récupérer les logs via {@code OrchestratorClient.getJobLogs(id)}
     * et passer le résultat à {@link #setLogSections(String, String)}.</p>
     */
    @FXML
    public void onReloadDetail() {
        if (currentJobKey == null || client == null) return;
        showLoading();
        String keyToLoad = currentJobKey;
        Task<JobRow> task = new Task<>() {
            @Override
            protected JobRow call() throws Exception {
                // Point d'extensibilité : remplacer par getJobLogs() quand disponible
                return client.getJobOrThrow(keyToLoad);
            }
        };
        task.setOnSucceeded(e -> Platform.runLater(() -> {
            JobRow row = task.getValue();
            String duration = JobDurationUtils.compute(row.getStartedAt(), row.getEndedAt());
            showDetail(row, duration);
            setLogSections(row.getErrorMessage(), row.getOutPdf());
        }));
        task.setOnFailed(e -> Platform.runLater(() ->
                showError("Erreur rechargement : " + task.getException().getMessage())));
        Thread t = new Thread(task, "detail-reload");
        t.setDaemon(true);
        t.start();
    }

    // -----------------------------------------------------------------------
    // Privé
    // -----------------------------------------------------------------------

    private void setVisibility(boolean empty, boolean loading,
                                boolean error, boolean content) {
        emptyLabel.setVisible(empty);     emptyLabel.setManaged(empty);
        loadingBox.setVisible(loading);   loadingBox.setManaged(loading);
        errorLabel.setVisible(error);     errorLabel.setManaged(error);
        detailContent.setVisible(content); detailContent.setManaged(content);
    }

    private static void copyToClipboard(String text) {
        ClipboardContent cc = new ClipboardContent();
        cc.putString(text);
        Clipboard.getSystemClipboard().setContent(cc);
    }
}

