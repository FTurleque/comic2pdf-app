package com.fturleque.comic2pdf.desktop;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fturleque.comic2pdf.desktop.duplicates.DuplicateDecision;
import com.fturleque.comic2pdf.desktop.duplicates.DuplicateService;
import javafx.geometry.Insets;
import javafx.scene.control.*;
import javafx.scene.layout.*;
import javafx.stage.DirectoryChooser;
import javafx.stage.FileChooser;

import java.awt.Desktop;
import java.io.File;
import java.io.IOException;
import java.nio.file.*;
import java.util.*;

public class MainView extends BorderPane {

    private final DuplicateService duplicateService = new DuplicateService(new ObjectMapper());

    private final TextField dataDirField = new TextField();
    private final TableView<DupRow> dupTable = new TableView<>();
    private final Label statusLabel = new Label("Ready.");

    /**
     * Constructeur par défaut : utilise {@code ../data} relatif au répertoire de lancement.
     * Délègue au constructeur {@link #MainView(String)}.
     */
    public MainView() {
        this(Paths.get("..", "data").normalize().toString());
    }

    /**
     * Constructeur avec chemin data/ initial explicite.
     * Utilisé par les tests (injection via {@code TestableMainApp}).
     *
     * @param initialDataDir Chemin initial du dossier data/.
     */
    public MainView(String initialDataDir) {
        setPadding(new Insets(10));

        var top = new VBox(8);
        top.getChildren().add(buildConfigRow());
        top.getChildren().add(buildActionsRow());
        setTop(top);

        setCenter(buildTable());
        setBottom(buildBottom());

        // IDs stables pour lookup TestFX
        dataDirField.setId("dataDirField");
        dupTable.setId("duplicatesTable");
        statusLabel.setId("mainStatusLabel");

        dataDirField.setText(initialDataDir);
        refreshDuplicates();
    }

    /**
     * Retourne le champ de saisie du chemin data/ (partagé avec les autres vues).
     *
     * @return Le {@code TextField} contenant le chemin du dossier data/.
     */
    public TextField getDataDirField() {
        return dataDirField;
    }

    private HBox buildConfigRow() {
        var chooseBtn = new Button("Choisir dossier data/");
        chooseBtn.setOnAction(e -> chooseDataDir());

        dataDirField.setPrefColumnCount(60);

        var refreshBtn = new Button("Rafraîchir doublons");
        refreshBtn.setId("duplicatesRefreshBtn");
        refreshBtn.setOnAction(e -> refreshDuplicates());

        var openOutBtn = new Button("Ouvrir out/");
        openOutBtn.setOnAction(e -> openDir(resolve("out")));

        var openInBtn = new Button("Ouvrir in/");
        openInBtn.setOnAction(e -> openDir(resolve("in")));

        var row = new HBox(8, new Label("DATA:"), dataDirField, chooseBtn, refreshBtn, openInBtn, openOutBtn);
        row.setPadding(new Insets(5));
        return row;
    }

    private HBox buildActionsRow() {
        var addBtn = new Button("Déposer un CBR/CBZ...");
        addBtn.setOnAction(e -> depositFile());

        var hint = new Label("Dépôt: copie en .part puis rename en .cbz/.cbr (fiable).");

        var row = new HBox(12, addBtn, hint);
        row.setPadding(new Insets(5));
        return row;
    }

    private VBox buildTable() {
        var colKey = new TableColumn<DupRow, String>("jobKey");
        colKey.setCellValueFactory(c -> c.getValue().jobKeyProperty());

        var colIncoming = new TableColumn<DupRow, String>("incoming");
        colIncoming.setCellValueFactory(c -> c.getValue().incomingFileProperty());

        var colExisting = new TableColumn<DupRow, String>("existingState");
        colExisting.setCellValueFactory(c -> c.getValue().existingStateProperty());

        var colAction = new TableColumn<DupRow, String>("Actions");
        colAction.setCellFactory(tc -> new TableCell<>() {
            private final Button useExisting = new Button("Utiliser existant");
            private final Button discard = new Button("Jeter");
            private final Button force = new Button("Forcer reprocess");

            {
                useExisting.setOnAction(e -> decide(getTableView().getItems().get(getIndex()), "USE_EXISTING_RESULT"));
                discard.setOnAction(e -> decide(getTableView().getItems().get(getIndex()), "DISCARD"));
                force.setOnAction(e -> decide(getTableView().getItems().get(getIndex()), "FORCE_REPROCESS"));
            }

            @Override
            protected void updateItem(String item, boolean empty) {
                super.updateItem(item, empty);
                if (empty) {
                    setGraphic(null);
                } else {
                    var box = new HBox(6, useExisting, discard, force);
                    setGraphic(box);
                }
            }
        });

        //noinspection unchecked // Safe: toutes les colonnes sont TableColumn<DupRow, String>
        dupTable.getColumns().addAll(colKey, colIncoming, colExisting, colAction);
        dupTable.setColumnResizePolicy(TableView.UNCONSTRAINED_RESIZE_POLICY);

        var container = new VBox(8, new Label("Doublons en attente (DUPLICATE_PENDING)"), dupTable);
        container.setPadding(new Insets(10, 5, 10, 5));
        return container;
    }

    private HBox buildBottom() {
        var row = new HBox(statusLabel);
        row.setPadding(new Insets(8));
        return row;
    }

    private void chooseDataDir() {
        var chooser = new DirectoryChooser();
        chooser.setTitle("Choisir le dossier data/");
        var dir = chooser.showDialog(getScene().getWindow());
        if (dir != null) {
            dataDirField.setText(dir.getAbsolutePath());
            refreshDuplicates();
        }
    }

    private Path resolve(String sub) {
        return Paths.get(dataDirField.getText()).resolve(sub);
    }

    private void openDir(Path dir) {
        try {
            Files.createDirectories(dir);
            if (Desktop.isDesktopSupported()) {
                Desktop.getDesktop().open(dir.toFile());
            }
        } catch (Exception ex) {
            statusLabel.setText("Erreur ouverture dossier: " + ex.getMessage());
        }
    }

    private void depositFile() {
        var fc = new FileChooser();
        fc.setTitle("Sélectionner un .cbz ou .cbr");
        fc.getExtensionFilters().addAll(
                new FileChooser.ExtensionFilter("Comic archives", "*.cbz", "*.cbr")
        );
        File f = fc.showOpenDialog(getScene().getWindow());
        if (f == null) return;

        Path inDir = resolve("in");
        try {
            Files.createDirectories(inDir);

            // Copy to .part then rename atomically
            String name = f.getName();
            Path part = inDir.resolve(name + ".part");
            Path fin = inDir.resolve(name);

            Files.copy(f.toPath(), part, StandardCopyOption.REPLACE_EXISTING);
            Files.move(part, fin, StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);

            statusLabel.setText("Déposé: " + fin);
        } catch (Exception ex) {
            statusLabel.setText("Erreur dépôt: " + ex.getMessage());
        }
    }

    private void refreshDuplicates() {
        try {
            List<DupRow> rows = duplicateService.listDuplicates(Paths.get(dataDirField.getText()));
            dupTable.getItems().setAll(rows);
            statusLabel.setText("Doublons: " + rows.size());
        } catch (IOException ex) {
            statusLabel.setText("Erreur lecture rapports: " + ex.getMessage());
        }
    }

    private void decide(DupRow row, String action) {
        String jobKey = row.getJobKey();
        try {
            DuplicateDecision decision = DuplicateDecision.valueOf(action);
            duplicateService.writeDecision(Paths.get(dataDirField.getText()), jobKey, decision);
            statusLabel.setText("Décision écrite: " + action + " (" + jobKey.substring(0, Math.min(12, jobKey.length())) + "...)");
        } catch (Exception ex) {
            statusLabel.setText("Erreur écriture décision: " + ex.getMessage());
        }
    }
}
