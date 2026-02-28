package com.fturleque.comic2pdf.desktop;

import javafx.application.Platform;
import javafx.collections.FXCollections;
import javafx.collections.ObservableList;
import javafx.concurrent.ScheduledService;
import javafx.concurrent.Task;
import javafx.geometry.Insets;
import javafx.scene.control.*;
import javafx.scene.layout.*;
import javafx.util.Duration;

import java.awt.Desktop;
import java.io.File;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * Vue JavaFX affichant l'état des jobs de l'orchestrateur.
 *
 * <p>Fonctionnalités :</p>
 * <ul>
 *   <li>TableView des jobs (jobKey, state, stage, attempt, updatedAt, fichier source)</li>
 *   <li>Refresh automatique toutes les 3 secondes via {@link ScheduledService} (pas de freeze UI)</li>
 *   <li>Bouton "Ouvrir dossier out/" pour ouvrir le dossier de sortie</li>
 *   <li>Indicateur de connexion à l'orchestrateur</li>
 * </ul>
 */
public class JobsView extends BorderPane {

    private final OrchestratorClient client;
    private final ObservableList<JobRow> rows = FXCollections.observableArrayList();
    private final TableView<JobRow> table = new TableView<>(rows);
    private final Label statusLabel = new Label("En attente...");
    private final TextField dataDirField;

    private ScheduledService<List<JobRow>> refreshService;

    /**
     * Construit la vue Jobs.
     *
     * @param client       Client HTTP vers l'orchestrateur.
     * @param dataDirField Champ partagé contenant le chemin du dossier data/ (depuis la vue principale).
     */
    public JobsView(OrchestratorClient client, TextField dataDirField) {
        this.client = client;
        this.dataDirField = dataDirField;
        setPadding(new Insets(10));
        buildUi();
        startRefreshService();
    }

    private void buildUi() {
        setTop(buildToolbar());
        setCenter(buildTable());
        setBottom(buildStatus());
    }

    private HBox buildToolbar() {
        var refreshBtn = new Button("Rafraîchir maintenant");
        refreshBtn.setOnAction(e -> forceRefresh());

        var openOutBtn = new Button("Ouvrir dossier out/");
        openOutBtn.setOnAction(e -> openOutDir());

        var row = new HBox(8, refreshBtn, openOutBtn);
        row.setPadding(new Insets(5));
        return row;
    }

    @SuppressWarnings("unchecked")
    private VBox buildTable() {
        var colKey = new TableColumn<JobRow, String>("Job Key");
        colKey.setCellValueFactory(c -> c.getValue().jobKeyProperty());
        colKey.setPrefWidth(220);

        var colFile = new TableColumn<JobRow, String>("Fichier");
        colFile.setCellValueFactory(c -> c.getValue().inputNameProperty());
        colFile.setPrefWidth(180);

        var colState = new TableColumn<JobRow, String>("État");
        colState.setCellValueFactory(c -> c.getValue().stateProperty());
        colState.setPrefWidth(120);

        var colStage = new TableColumn<JobRow, String>("Étape");
        colStage.setCellValueFactory(c -> c.getValue().stageProperty());
        colStage.setPrefWidth(120);

        var colAttempt = new TableColumn<JobRow, String>("Tentative");
        colAttempt.setCellValueFactory(c -> c.getValue().attemptProperty());
        colAttempt.setPrefWidth(80);

        var colUpdated = new TableColumn<JobRow, String>("Mis à jour");
        colUpdated.setCellValueFactory(c -> c.getValue().updatedAtProperty());
        colUpdated.setPrefWidth(160);

        table.getColumns().addAll(colKey, colFile, colState, colStage, colAttempt, colUpdated);
        table.setColumnResizePolicy(TableView.CONSTRAINED_RESIZE_POLICY);
        table.setPlaceholder(new Label("Aucun job. Vérifier la connexion à l'orchestrateur."));

        var container = new VBox(8, new Label("Jobs de l'orchestrateur"), table);
        container.setPadding(new Insets(5));
        return container;
    }

    private HBox buildStatus() {
        var row = new HBox(statusLabel);
        row.setPadding(new Insets(8));
        return row;
    }

    /**
     * Démarre le service de refresh automatique toutes les 3 secondes.
     * Utilise {@link ScheduledService} JavaFX pour ne pas bloquer le thread UI.
     */
    private void startRefreshService() {
        refreshService = new ScheduledService<>() {
            @Override
            protected Task<List<JobRow>> createTask() {
                return new Task<>() {
                    @Override
                    protected List<JobRow> call() {
                        return client.getJobs();
                    }
                };
            }
        };
        refreshService.setPeriod(Duration.seconds(3));
        refreshService.setOnSucceeded(e -> {
            @SuppressWarnings("unchecked")
            List<JobRow> freshRows = (List<JobRow>) e.getSource().getValue();
            updateTable(freshRows);
            statusLabel.setText("Rafraîchi : " + java.time.LocalTime.now().withNano(0));
        });
        refreshService.setOnFailed(e -> {
            Throwable ex = e.getSource().getException();
            statusLabel.setText("Erreur connexion orchestrateur : " +
                    (ex != null ? ex.getMessage() : "inconnue"));
        });
        refreshService.start();
    }

    /**
     * Force un refresh immédiat (hors du cycle périodique).
     */
    public void forceRefresh() {
        List<JobRow> fresh = client.getJobs();
        updateTable(fresh);
        statusLabel.setText("Rafraîchi manuellement.");
    }

    /**
     * Met à jour la {@link TableView} en préservant les lignes existantes (mise à jour in-place).
     * Appel garanti sur le thread JavaFX.
     *
     * @param freshRows Nouvelle liste de jobs reçue de l'orchestrateur.
     */
    private void updateTable(List<JobRow> freshRows) {
        Platform.runLater(() -> {
            // Index les lignes existantes par jobKey pour mise à jour in-place
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
            // Supprimer les lignes qui ne sont plus dans la réponse
            rows.removeIf(r -> freshRows.stream().noneMatch(f -> f.getJobKey().equals(r.getJobKey())));
        });
    }

    /**
     * Ouvre le dossier {@code data/out/} dans l'explorateur système.
     */
    private void openOutDir() {
        Path outDir = Paths.get(dataDirField.getText()).resolve("out");
        try {
            Files.createDirectories(outDir);
            File f = outDir.toFile();
            if (Desktop.isDesktopSupported()) {
                Desktop.getDesktop().open(f);
            }
        } catch (Exception ex) {
            statusLabel.setText("Erreur ouverture dossier : " + ex.getMessage());
        }
    }

    /**
     * Arrête le service de refresh (à appeler lors de la fermeture de la fenêtre).
     */
    public void stop() {
        if (refreshService != null) {
            refreshService.cancel();
        }
    }
}

