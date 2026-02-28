package com.comic2pdf.desktop.ui.controller;

import com.comic2pdf.desktop.model.JobRow;
import com.comic2pdf.desktop.service.AppServices;
import com.comic2pdf.desktop.util.FxUtils;
import javafx.application.Platform;
import javafx.collections.FXCollections;
import javafx.collections.ObservableList;
import javafx.concurrent.ScheduledService;
import javafx.concurrent.Task;
import javafx.fxml.FXML;
import javafx.scene.control.Label;
import javafx.scene.control.TableColumn;
import javafx.scene.control.TableView;
import javafx.util.Duration;

import java.nio.file.Paths;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * Controller de l'onglet Jobs.
 *
 * <p>Polling automatique toutes les 3 secondes via {@link ScheduledService} (sans freeze UI).
 * Désactivable pour les tests via {@link #setAutoRefresh(boolean)} (à appeler
 * AVANT {@link #setServices(AppServices)}).</p>
 */
public class JobsController {

    @FXML private TableView<JobRow> jobsTable;
    @FXML private Label jobsStatusLabel;

    private AppServices services;
    private boolean autoRefresh = true;
    private ScheduledService<List<JobRow>> refreshService;
    private final ObservableList<JobRow> rows = FXCollections.observableArrayList();

    /**
     * Initialisation FXML : configure les colonnes et lie la liste observable.
     */
    @FXML
    public void initialize() {
        TableColumn<JobRow, String> colKey = new TableColumn<>("Job Key");
        colKey.setCellValueFactory(c -> c.getValue().jobKeyProperty());
        colKey.setPrefWidth(220);

        TableColumn<JobRow, String> colFile = new TableColumn<>("Fichier");
        colFile.setCellValueFactory(c -> c.getValue().inputNameProperty());
        colFile.setPrefWidth(180);

        TableColumn<JobRow, String> colState = new TableColumn<>("État");
        colState.setCellValueFactory(c -> c.getValue().stateProperty());
        colState.setPrefWidth(120);

        TableColumn<JobRow, String> colStage = new TableColumn<>("Étape");
        colStage.setCellValueFactory(c -> c.getValue().stageProperty());
        colStage.setPrefWidth(120);

        TableColumn<JobRow, String> colAttempt = new TableColumn<>("Tentative");
        colAttempt.setCellValueFactory(c -> c.getValue().attemptProperty());
        colAttempt.setPrefWidth(80);

        TableColumn<JobRow, String> colUpdated = new TableColumn<>("Mis à jour");
        colUpdated.setCellValueFactory(c -> c.getValue().updatedAtProperty());
        colUpdated.setPrefWidth(160);

        //noinspection unchecked
        jobsTable.getColumns().addAll(colKey, colFile, colState, colStage, colAttempt, colUpdated);
        jobsTable.setColumnResizePolicy(TableView.UNCONSTRAINED_RESIZE_POLICY);
        jobsTable.setItems(rows);
    }

    /**
     * Injecte les services et démarre le polling si {@code autoRefresh=true}.
     * Doit être appelé APRÈS {@link #setAutoRefresh(boolean)}.
     *
     * @param services Services partagés de l'application.
     */
    public void setServices(AppServices services) {
        this.services = services;
        if (autoRefresh) {
            startRefreshService();
        }
    }

    /**
     * Active ou désactive le polling automatique.
     * Doit être appelé AVANT {@link #setServices(AppServices)}.
     *
     * @param autoRefresh {@code false} pour désactiver le polling (utile en tests).
     */
    public void setAutoRefresh(boolean autoRefresh) {
        this.autoRefresh = autoRefresh;
    }

    /** Rafraîchit manuellement la liste des jobs depuis l'orchestrateur. */
    @FXML
    public void onRefreshJobs() {
        if (services == null) return;
        List<JobRow> fresh = services.getOrchestratorClient().getJobs();
        updateTable(fresh);
        jobsStatusLabel.setText("Rafraîchi manuellement.");
    }

    /** Ouvre le dossier {@code data/out/} dans l'explorateur système. */
    @FXML
    private void onOpenOutDir() {
        if (services == null) return;
        FxUtils.openDirectory(Paths.get(services.getInitialDataDir()).resolve("out"));
    }

    /**
     * Arrête le service de polling (à appeler lors de la fermeture de la fenêtre).
     */
    public void stop() {
        if (refreshService != null) {
            refreshService.cancel();
        }
    }

    // -----------------------------------------------------------------------
    // Helpers privés
    // -----------------------------------------------------------------------

    private void startRefreshService() {
        refreshService = new ScheduledService<>() {
            @Override
            protected Task<List<JobRow>> createTask() {
                return new Task<>() {
                    @Override
                    protected List<JobRow> call() {
                        return services.getOrchestratorClient().getJobs();
                    }
                };
            }
        };
        refreshService.setPeriod(Duration.seconds(3));
        refreshService.setOnSucceeded(e -> {
            @SuppressWarnings("unchecked")
            List<JobRow> freshRows = (List<JobRow>) e.getSource().getValue();
            updateTable(freshRows);
            jobsStatusLabel.setText("Rafraîchi : " + java.time.LocalTime.now().withNano(0));
        });
        refreshService.setOnFailed(e -> {
            Throwable ex = e.getSource().getException();
            jobsStatusLabel.setText("Erreur connexion orchestrateur : "
                    + (ex != null ? ex.getMessage() : "inconnue"));
        });
        refreshService.start();
    }

    private void updateTable(List<JobRow> freshRows) {
        Platform.runLater(() -> {
            Map<String, JobRow> existing = rows.stream()
                    .collect(Collectors.toMap(JobRow::getJobKey, r -> r));
            for (JobRow fresh : freshRows) {
                JobRow cur = existing.remove(fresh.getJobKey());
                if (cur != null) {
                    cur.updateFrom(fresh);
                } else {
                    rows.add(fresh);
                }
            }
            rows.removeIf(r -> freshRows.stream()
                    .noneMatch(f -> f.getJobKey().equals(r.getJobKey())));
        });
    }
}

