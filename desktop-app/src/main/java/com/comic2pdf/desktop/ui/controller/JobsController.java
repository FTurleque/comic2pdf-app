package com.comic2pdf.desktop.ui.controller;

import com.comic2pdf.desktop.model.JobRow;
import com.comic2pdf.desktop.service.AppServices;
import com.comic2pdf.desktop.util.FxUtils;
import javafx.animation.PauseTransition;
import javafx.application.Platform;
import javafx.collections.FXCollections;
import javafx.collections.ObservableList;
import javafx.collections.transformation.FilteredList;
import javafx.collections.transformation.SortedList;
import javafx.concurrent.ScheduledService;
import javafx.concurrent.Task;
import javafx.fxml.FXML;
import javafx.scene.control.*;
import javafx.scene.input.Clipboard;
import javafx.scene.input.ClipboardContent;
import javafx.util.Duration;

import java.nio.file.Paths;
import java.time.LocalTime;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * Controller de l'onglet Jobs.
 *
 * <p>Fonctionnalités :</p>
 * <ul>
 *   <li>Polling automatique toutes les 3 secondes via {@link ScheduledService} (sans freeze UI).</li>
 *   <li>Backoff exponentiel si l'orchestrateur est indisponible (3s → 6s → 12s → max 30s).</li>
 *   <li>Bannière "offline" visible si l'orchestrateur est inaccessible.</li>
 *   <li>Recherche textuelle sur jobKey / nom de fichier.</li>
 *   <li>Filtres par état (ALL / DONE / ERROR / RUNNING / WAITING).</li>
 *   <li>Panneau de détail enrichi au clic sur une ligne.</li>
 * </ul>
 */
public class JobsController {

    // Intervalles de backoff (secondes)
    private static final double REFRESH_INTERVAL_BASE = 3.0;
    private static final double REFRESH_INTERVAL_MAX = 30.0;

    @FXML private TableView<JobRow> jobsTable;
    @FXML private Label jobsStatusLabel;
    @FXML private Label offlineBanner;
    @FXML private TextField jobSearchField;
    @FXML private ComboBox<String> jobStateFilter;

    // Panneau de détail
    @FXML private Label detailJobKey;
    @FXML private Label detailState;
    @FXML private Label detailStage;
    @FXML private Label detailAttempt;
    @FXML private Label detailUpdatedAt;
    @FXML private Label detailInputName;
    @FXML private Label detailOutPdf;
    @FXML private Label detailError;

    private AppServices services;
    private boolean autoRefresh = true;
    private ScheduledService<List<JobRow>> refreshService;
    private final ObservableList<JobRow> rows = FXCollections.observableArrayList();
    private FilteredList<JobRow> filteredRows;
    private double currentIntervalSeconds = REFRESH_INTERVAL_BASE;
    private boolean isOffline = false;

    /**
     * Initialisation FXML : configure les colonnes, la recherche, les filtres et le panneau détail.
     */
    @FXML
    public void initialize() {
        // Colonnes de la table
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
        colAttempt.setPrefWidth(70);

        TableColumn<JobRow, String> colUpdated = new TableColumn<>("Mis à jour");
        colUpdated.setCellValueFactory(c -> c.getValue().updatedAtProperty());
        colUpdated.setPrefWidth(160);

        //noinspection unchecked
        jobsTable.getColumns().addAll(colKey, colFile, colState, colStage, colAttempt, colUpdated);
        jobsTable.setColumnResizePolicy(TableView.UNCONSTRAINED_RESIZE_POLICY);

        // Filtrage et recherche
        filteredRows = new FilteredList<>(rows, p -> true);
        SortedList<JobRow> sortedRows = new SortedList<>(filteredRows);
        sortedRows.comparatorProperty().bind(jobsTable.comparatorProperty());
        jobsTable.setItems(sortedRows);

        // Filtres état
        if (jobStateFilter != null) {
            jobStateFilter.getItems().addAll("Tous", "DONE", "ERROR", "RUNNING", "QUEUED");
            jobStateFilter.setValue("Tous");
            jobStateFilter.valueProperty().addListener((obs, o, n) -> updateFilter());
        }

        // Recherche textuelle
        if (jobSearchField != null) {
            jobSearchField.textProperty().addListener((obs, o, n) -> updateFilter());
        }

        // Sélection → panneau détail
        jobsTable.getSelectionModel().selectedItemProperty().addListener(
                (obs, old, selected) -> showDetail(selected));

        // Bannière offline masquée par défaut
        if (offlineBanner != null) {
            offlineBanner.setVisible(false);
            offlineBanner.setManaged(false);
        }
    }

    /**
     * Injecte les services et démarre le polling si {@code autoRefresh=true}.
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
        jobsStatusLabel.setText("Rafraîchi manuellement à " + LocalTime.now().withNano(0));
    }

    /** Ouvre le dossier {@code data/out/} dans l'explorateur système. */
    @FXML
    private void onOpenOutDir() {
        if (services == null) return;
        FxUtils.openDirectory(Paths.get(services.getInitialDataDir()).resolve("out"));
    }

    /** Copie le jobKey du job sélectionné dans le presse-papiers. */
    @FXML
    private void onCopyJobKey() {
        JobRow selected = jobsTable.getSelectionModel().getSelectedItem();
        if (selected == null || selected.getJobKey().isBlank()) return;
        copyToClipboard(selected.getJobKey());
        jobsStatusLabel.setText("JobKey copié : " + abbreviate(selected.getJobKey(), 20));
    }

    /** Copie le message d'erreur du job sélectionné. */
    @FXML
    private void onCopyError() {
        JobRow selected = jobsTable.getSelectionModel().getSelectedItem();
        if (selected == null || selected.getErrorMessage().isBlank()) {
            jobsStatusLabel.setText("Aucune erreur à copier.");
            return;
        }
        copyToClipboard(selected.getErrorMessage());
        jobsStatusLabel.setText("Erreur copiée.");
    }

    /** Ouvre le dossier work/ du job sélectionné. */
    @FXML
    private void onOpenWorkDir() {
        JobRow selected = jobsTable.getSelectionModel().getSelectedItem();
        if (selected == null) return;
        FxUtils.openDirectory(Paths.get(services.getInitialDataDir())
                .resolve("work").resolve(selected.getJobKey()));
    }

    /** Ouvre le fichier PDF de sortie du job sélectionné. */
    @FXML
    private void onOpenOutPdf() {
        JobRow selected = jobsTable.getSelectionModel().getSelectedItem();
        if (selected == null || selected.getOutPdf().isBlank()) {
            jobsStatusLabel.setText("Pas de PDF disponible pour ce job.");
            return;
        }
        FxUtils.openFile(Paths.get(selected.getOutPdf()));
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
        refreshService.setPeriod(Duration.seconds(currentIntervalSeconds));
        refreshService.setOnSucceeded(e -> {
            @SuppressWarnings("unchecked")
            List<JobRow> freshRows = (List<JobRow>) e.getSource().getValue();
            updateTable(freshRows);
            jobsStatusLabel.setText("Rafraîchi : " + LocalTime.now().withNano(0));
            // Reconnexion : reset du backoff
            if (isOffline) {
                isOffline = false;
                currentIntervalSeconds = REFRESH_INTERVAL_BASE;
                refreshService.setPeriod(Duration.seconds(currentIntervalSeconds));
                setOfflineBanner(false);
            }
        });
        refreshService.setOnFailed(e -> {
            Throwable ex = e.getSource().getException();
            String msg = ex != null ? ex.getMessage() : "inconnue";
            jobsStatusLabel.setText("Orchestrateur inaccessible : " + msg);
            // Backoff exponentiel
            isOffline = true;
            currentIntervalSeconds = Math.min(currentIntervalSeconds * 2, REFRESH_INTERVAL_MAX);
            refreshService.setPeriod(Duration.seconds(currentIntervalSeconds));
            setOfflineBanner(true);
        });
        refreshService.start();
    }

    private void setOfflineBanner(boolean visible) {
        if (offlineBanner != null) {
            offlineBanner.setVisible(visible);
            offlineBanner.setManaged(visible);
        }
    }

    private void updateFilter() {
        String search = jobSearchField != null ? jobSearchField.getText().toLowerCase().trim() : "";
        String stateFilter = jobStateFilter != null ? jobStateFilter.getValue() : "Tous";

        filteredRows.setPredicate(row -> {
            boolean matchSearch = search.isEmpty()
                    || row.getJobKey().toLowerCase().contains(search)
                    || row.getInputName().toLowerCase().contains(search);
            boolean matchState = "Tous".equals(stateFilter)
                    || row.getState().equalsIgnoreCase(stateFilter);
            return matchSearch && matchState;
        });
    }

    private void showDetail(JobRow row) {
        if (row == null) {
            clearDetail();
            return;
        }
        if (detailJobKey != null) detailJobKey.setText(row.getJobKey());
        if (detailState != null) detailState.setText(row.getState());
        if (detailStage != null) detailStage.setText(row.getStage());
        if (detailAttempt != null) detailAttempt.setText(row.getAttempt());
        if (detailUpdatedAt != null) detailUpdatedAt.setText(row.getUpdatedAt());
        if (detailInputName != null) detailInputName.setText(row.getInputName());
        if (detailOutPdf != null) detailOutPdf.setText(row.getOutPdf());
        if (detailError != null) detailError.setText(row.getErrorMessage());
    }

    private void clearDetail() {
        Label[] labels = { detailJobKey, detailState, detailStage, detailAttempt,
                           detailUpdatedAt, detailInputName, detailOutPdf, detailError };
        for (Label l : labels) {
            if (l != null) l.setText("");
        }
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

    private static void copyToClipboard(String text) {
        ClipboardContent content = new ClipboardContent();
        content.putString(text);
        Clipboard.getSystemClipboard().setContent(content);
    }

    private static String abbreviate(String s, int maxLen) {
        return s.length() <= maxLen ? s : s.substring(0, maxLen) + "...";
    }
}
