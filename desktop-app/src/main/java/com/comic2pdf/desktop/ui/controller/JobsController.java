package com.comic2pdf.desktop.ui.controller;

import com.comic2pdf.desktop.model.JobRow;
import com.comic2pdf.desktop.service.AppServices;
import com.comic2pdf.desktop.service.ConnectivityService;
import com.comic2pdf.desktop.util.FxUtils;
import com.comic2pdf.desktop.util.JobDurationUtils;
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
import javafx.scene.layout.HBox;
import javafx.util.Duration;

import java.nio.file.Paths;
import java.time.LocalTime;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicLong;
import java.util.stream.Collectors;

/**
 * Controller de l'onglet Jobs.
 *
 * <p>Fonctionnalités :</p>
 * <ul>
 *   <li>Polling automatique via {@link ScheduledService} avec backoff exponentiel.</li>
 *   <li>Refresh manuel async (Task + Platform.runLater) compatible test {@code < 3s}.</li>
 *   <li>Recherche textuelle avec debounce 250 ms + filtre par état ({@link FilteredList}).</li>
 *   <li>Panneau latéral de détail via {@link JobDetailPanelController} ({@code fx:include}).</li>
 *   <li>Bannière offline + retry via {@link ConnectivityService} (toutes mutations FX thread).</li>
 * </ul>
 */
public class JobsController {

    // Intervalles de backoff (secondes)
    private static final double REFRESH_INTERVAL_BASE = 3.0;
    private static final double REFRESH_INTERVAL_MAX  = 30.0;

    // -----------------------------------------------------------------------
    // FXML — IDs STABLES (NE PAS RENOMMER — compatibilité tests UI)
    // -----------------------------------------------------------------------
    @FXML private TableView<JobRow> jobsTable;
    @FXML private Label             jobsStatusLabel;

    // -----------------------------------------------------------------------
    // FXML — Bannière offline
    // -----------------------------------------------------------------------
    @FXML private HBox  offlineBannerBox;
    @FXML private Label offlineReasonLabel;

    // -----------------------------------------------------------------------
    // FXML — Recherche et filtres
    // -----------------------------------------------------------------------
    @FXML private TextField        jobSearchField;
    @FXML private ComboBox<String> jobStateFilter;

    // -----------------------------------------------------------------------
    // FXML — Panneau détail (injecté via fx:include)
    // -----------------------------------------------------------------------
    @FXML private JobDetailPanelController jobDetailPanelController;

    // -----------------------------------------------------------------------
    // État interne
    // -----------------------------------------------------------------------
    private AppServices        services;
    private ConnectivityService connectivityService;
    private boolean            autoRefresh = true;

    private final ObservableList<JobRow> masterList      = FXCollections.observableArrayList();
    private FilteredList<JobRow>         filteredList;
    private final AtomicLong             detailRequestSeq = new AtomicLong(0);

    private ScheduledService<List<JobRow>> scheduledRefresh;
    private double currentIntervalS = REFRESH_INTERVAL_BASE;

    // -----------------------------------------------------------------------
    // Initialisation
    // -----------------------------------------------------------------------

    /**
     * Initialisation FXML : configure colonnes, filtres, sélection, bannière.
     */
    @FXML
    public void initialize() {
        buildColumns();

        // FilteredList + SortedList — tri conservé
        filteredList = new FilteredList<>(masterList, p -> true);
        SortedList<JobRow> sortedList = new SortedList<>(filteredList);
        sortedList.comparatorProperty().bind(jobsTable.comparatorProperty());
        jobsTable.setItems(sortedList);

        // Défensive : si les contrôles de recherche / filtre ne sont pas injectés via FXML,
        // créer des instances locales pour éviter NPE (utile pour certains environnements de test).
        if (jobStateFilter == null) {
            jobStateFilter = new ComboBox<>();
        }
        if (jobSearchField == null) {
            jobSearchField = new TextField();
        }

        // ComboBox états
        jobStateFilter.getItems().addAll(
                "Tous", "DONE", "ERROR", "PREP_RUNNING", "OCR_RUNNING",
                "QUEUED", "DUPLICATE_PENDING");
        jobStateFilter.setValue("Tous");
        jobStateFilter.valueProperty().addListener((o, ov, nv) -> applyFilter());

        // Recherche avec debounce 250 ms
        PauseTransition debounce = new PauseTransition(Duration.millis(250));
        debounce.setOnFinished(e -> applyFilter());
        jobSearchField.textProperty().addListener((o, ov, nv) -> {
            debounce.stop();
            debounce.playFromStart();
        });

        // Sélection ligne → chargement panneau détail
        jobsTable.getSelectionModel().selectedItemProperty()
                .addListener((o, old, sel) -> onRowSelected(sel));

        // Bannière offline masquée par défaut
        setOfflineBannerVisible(false, "");
    }

    /**
     * Injecte les services, lie la bannière offline et démarre le polling.
     *
     * @param services Services partagés de l'application.
     */
    public void setServices(AppServices services) {
        this.services = services;

        // ConnectivityService thread-safe
        connectivityService = new ConnectivityService(services.getOrchestratorClient());
        connectivityService.setOnComeOnline(this::onRefreshJobs);
        connectivityService.onlineProperty().addListener((o, ov, online) -> {
            assert Platform.isFxApplicationThread();
            if (online) {
                setOfflineBannerVisible(false, "");
            } else {
                setOfflineBannerVisible(true,
                        connectivityService.offlineReasonProperty().get());
            }
        });

        // Injecter le client dans le panneau détail
        if (jobDetailPanelController != null) {
            jobDetailPanelController.setClient(services.getOrchestratorClient());
        }

        if (autoRefresh) {
            startScheduledRefresh();
        }
    }

    /**
     * Active ou désactive le polling automatique.
     * Doit être appelé AVANT {@link #setServices(AppServices)}.
     *
     * @param autoRefresh false pour désactiver (utile en tests).
     */
    public void setAutoRefresh(boolean autoRefresh) {
        this.autoRefresh = autoRefresh;
    }

    // -----------------------------------------------------------------------
    // Actions FXML
    // -----------------------------------------------------------------------

    /**
     * Rafraîchit manuellement la liste des jobs.
     * Exécuté en async (Task + Platform.runLater) — ne bloque pas le FX thread.
     * Compatible test : aucun Thread.sleep, completion &lt; 3s.
     */
    @FXML
    public void onRefreshJobs() {
        if (services == null) return;
        Task<List<JobRow>> task = new Task<>() {
            @Override
            protected List<JobRow> call() throws Exception {
                return services.getOrchestratorClient().getJobsOrThrow();
            }
        };
        task.setOnSucceeded(e -> Platform.runLater(() -> {
            @SuppressWarnings("unchecked")
            List<JobRow> fresh = (List<JobRow>) e.getSource().getValue();
            updateMasterList(fresh);
            jobsStatusLabel.setText("Rafraîchi : " + LocalTime.now().withNano(0));
            connectivityService.markOnline();
            currentIntervalS = REFRESH_INTERVAL_BASE;
        }));
        task.setOnFailed(e -> Platform.runLater(() -> {
            String msg = task.getException() != null
                    ? task.getException().getMessage() : "erreur inconnue";
            jobsStatusLabel.setText("Inaccessible : " + msg);
            connectivityService.markOffline(msg);
            // masterList conservée — pas de vidage
        }));
        Thread t = new Thread(task, "jobs-refresh");
        t.setDaemon(true);
        t.start();
    }

    /** Efface la recherche et le filtre état. */
    @FXML
    private void onClearFilter() {
        jobSearchField.setText("");
        jobStateFilter.setValue("Tous");
    }

    /** Ouvre le dossier {@code data/out/} dans l'explorateur système. */
    @FXML
    private void onOpenOutDir() {
        if (services == null) return;
        FxUtils.openDirectory(Paths.get(services.getInitialDataDir()).resolve("out"));
    }

    /**
     * Arrête le polling et le ConnectivityService.
     * À appeler lors de la fermeture de la fenêtre.
     */
    public void stop() {
        if (scheduledRefresh != null) scheduledRefresh.cancel();
        if (connectivityService != null) connectivityService.shutdown();
    }

    // -----------------------------------------------------------------------
    // Privé — sélection et panneau détail
    // -----------------------------------------------------------------------

    private void onRowSelected(JobRow row) {
        if (jobDetailPanelController == null) return;
        if (row == null) {
            jobDetailPanelController.showEmpty();
            return;
        }
        long seq = detailRequestSeq.incrementAndGet();
        jobDetailPanelController.showLoading();

        Task<JobRow> task = new Task<>() {
            @Override
            protected JobRow call() throws Exception {
                return services.getOrchestratorClient().getJobOrThrow(row.getJobKey());
            }
        };
        task.setOnSucceeded(e -> Platform.runLater(() -> {
            if (detailRequestSeq.get() != seq) return; // sélection obsolète
            JobRow detail = task.getValue();
            String duration = JobDurationUtils.compute(
                    detail.getStartedAt(), detail.getEndedAt());
            jobDetailPanelController.showDetail(detail, duration);
            jobDetailPanelController.setLogSections(
                    detail.getErrorMessage(), detail.getOutPdf());
        }));
        task.setOnFailed(e -> Platform.runLater(() -> {
            if (detailRequestSeq.get() != seq) return;
            // Repli : afficher données de la liste (déjà chargées)
            String duration = JobDurationUtils.compute(
                    row.getStartedAt(), row.getEndedAt());
            jobDetailPanelController.showDetail(row, duration);
            jobDetailPanelController.setLogSections(
                    row.getErrorMessage(), row.getOutPdf());
        }));
        Thread t = new Thread(task, "detail-load");
        t.setDaemon(true);
        t.start();
    }

    // -----------------------------------------------------------------------
    // Privé — polling automatique
    // -----------------------------------------------------------------------

    private void startScheduledRefresh() {
        scheduledRefresh = new ScheduledService<>() {
            @Override
            protected Task<List<JobRow>> createTask() {
                return new Task<>() {
                    @Override
                    protected List<JobRow> call() throws Exception {
                        return services.getOrchestratorClient().getJobsOrThrow();
                    }
                };
            }
        };
        scheduledRefresh.setPeriod(Duration.seconds(currentIntervalS));
        scheduledRefresh.setOnSucceeded(e -> {
            @SuppressWarnings("unchecked")
            List<JobRow> fresh = (List<JobRow>) e.getSource().getValue();
            Platform.runLater(() -> {
                updateMasterList(fresh);
                jobsStatusLabel.setText("Rafraîchi : " + LocalTime.now().withNano(0));
                if (!connectivityService.isOnline()) {
                    connectivityService.markOnline();
                    currentIntervalS = REFRESH_INTERVAL_BASE;
                    scheduledRefresh.setPeriod(Duration.seconds(currentIntervalS));
                }
            });
        });
        scheduledRefresh.setOnFailed(e -> Platform.runLater(() -> {
            currentIntervalS = Math.min(currentIntervalS * 2, REFRESH_INTERVAL_MAX);
            scheduledRefresh.setPeriod(Duration.seconds(currentIntervalS));
            String msg = e.getSource().getException() != null
                    ? e.getSource().getException().getMessage() : "inconnue";
            jobsStatusLabel.setText("Inaccessible : " + msg);
            connectivityService.markOffline(msg);
        }));
        scheduledRefresh.start();
    }

    // -----------------------------------------------------------------------
    // Privé — helpers
    // -----------------------------------------------------------------------

    private void applyFilter() {
        String search = jobSearchField.getText().toLowerCase().trim();
        String state  = jobStateFilter.getValue();
        filteredList.setPredicate(row -> {
            boolean matchSearch = search.isEmpty()
                    || row.getJobKey().toLowerCase().contains(search)
                    || row.getInputName().toLowerCase().contains(search);
            boolean matchState = "Tous".equals(state)
                    || row.getState().equalsIgnoreCase(state);
            return matchSearch && matchState;
        });
    }

    private void updateMasterList(List<JobRow> freshRows) {
        assert Platform.isFxApplicationThread();
        Map<String, JobRow> existing = masterList.stream()
                .collect(Collectors.toMap(JobRow::getJobKey, r -> r));
        for (JobRow fresh : freshRows) {
            JobRow cur = existing.remove(fresh.getJobKey());
            if (cur != null) {
                cur.updateFrom(fresh);
            } else {
                masterList.add(fresh);
            }
        }
        masterList.removeIf(r -> freshRows.stream()
                .noneMatch(f -> f.getJobKey().equals(r.getJobKey())));
    }

    private void buildColumns() {
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
        colStage.setPrefWidth(100);

        TableColumn<JobRow, String> colAttempt = new TableColumn<>("Tentative");
        colAttempt.setCellValueFactory(c -> c.getValue().attemptProperty());
        colAttempt.setPrefWidth(70);

        TableColumn<JobRow, String> colUpdated = new TableColumn<>("Mis à jour");
        colUpdated.setCellValueFactory(c -> c.getValue().updatedAtProperty());
        colUpdated.setPrefWidth(160);

        //noinspection unchecked
        jobsTable.getColumns().addAll(colKey, colFile, colState, colStage, colAttempt, colUpdated);
        jobsTable.setColumnResizePolicy(TableView.UNCONSTRAINED_RESIZE_POLICY);
    }

    private void setOfflineBannerVisible(boolean visible, String reason) {
        assert Platform.isFxApplicationThread();
        if (offlineBannerBox != null) {
            offlineBannerBox.setVisible(visible);
            offlineBannerBox.setManaged(visible);
        }
        if (offlineReasonLabel != null && reason != null) {
            offlineReasonLabel.setText(reason);
        }
    }
}
