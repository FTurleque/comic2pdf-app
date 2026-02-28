package com.comic2pdf.desktop.ui.controller;

import com.comic2pdf.desktop.model.DupRow;
import com.comic2pdf.desktop.model.DuplicateDecision;
import com.comic2pdf.desktop.service.AppServices;
import com.comic2pdf.desktop.util.FxUtils;
import javafx.fxml.FXML;
import javafx.scene.control.Button;
import javafx.scene.control.Label;
import javafx.scene.control.TableCell;
import javafx.scene.control.TableColumn;
import javafx.scene.control.TableView;
import javafx.scene.control.TextField;
import javafx.scene.layout.HBox;
import javafx.stage.DirectoryChooser;
import javafx.stage.FileChooser;

import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;
import java.util.List;

/**
 * Controller de l'onglet Doublons.
 *
 * <p>Délègue toute logique filesystem à {@code DuplicateService} (pur, testable).
 * Gère le dépôt de fichiers via convention {@code .part → .cbz/.cbr} (rename atomique).</p>
 */
public class DuplicatesController {

    @FXML private TextField dataDirField;
    @FXML private TableView<DupRow> duplicatesTable;
    @FXML private Label duplicatesStatusLabel;

    private AppServices services;

    /**
     * Initialisation FXML : configure les colonnes de la TableView.
     * Les colonnes sont créées en Java (lambda CellValueFactory non supportée en FXML pur).
     */
    @FXML
    public void initialize() {
        TableColumn<DupRow, String> colKey = new TableColumn<>("jobKey");
        colKey.setCellValueFactory(c -> c.getValue().jobKeyProperty());
        colKey.setPrefWidth(220);

        TableColumn<DupRow, String> colIncoming = new TableColumn<>("Fichier entrant");
        colIncoming.setCellValueFactory(c -> c.getValue().incomingFileProperty());
        colIncoming.setPrefWidth(180);

        TableColumn<DupRow, String> colState = new TableColumn<>("État existant");
        colState.setCellValueFactory(c -> c.getValue().existingStateProperty());
        colState.setPrefWidth(120);

        TableColumn<DupRow, String> colActions = buildActionsColumn();

        //noinspection unchecked
        duplicatesTable.getColumns().addAll(colKey, colIncoming, colState, colActions);
        duplicatesTable.setColumnResizePolicy(TableView.UNCONSTRAINED_RESIZE_POLICY);
    }

    /**
     * Injecte le conteneur de services.
     *
     * @param services Services partagés de l'application.
     */
    public void setServices(AppServices services) {
        this.services = services;
    }

    /**
     * Définit le chemin initial du dossier data/ et déclenche un premier refresh.
     * Doit être appelé après {@link #setServices(AppServices)}.
     *
     * @param dataDir Chemin du dossier data/.
     */
    public void setInitialDataDir(String dataDir) {
        dataDirField.setText(dataDir);
        refreshDuplicates();
    }

    /** Ouvre le sélecteur de dossier data/. */
    @FXML
    private void onChooseDataDir() {
        DirectoryChooser chooser = new DirectoryChooser();
        chooser.setTitle("Choisir le dossier data/");
        File dir = chooser.showDialog(dataDirField.getScene().getWindow());
        if (dir != null) {
            dataDirField.setText(dir.getAbsolutePath());
            refreshDuplicates();
        }
    }

    /** Rafraîchit la liste des doublons depuis {@code data/reports/duplicates/}. */
    @FXML
    public void onRefreshDuplicates() {
        refreshDuplicates();
    }

    /** Ouvre {@code data/in/} dans l'explorateur système. */
    @FXML
    private void onOpenInFolder() {
        FxUtils.openDirectory(resolve("in"));
    }

    /** Ouvre {@code data/out/} dans l'explorateur système. */
    @FXML
    private void onOpenOutFolder() {
        FxUtils.openDirectory(resolve("out"));
    }

    /**
     * Dépose un CBZ/CBR dans {@code data/in/}.
     * Convention : copie en {@code .part} puis rename atomique.
     */
    @FXML
    private void onDepositFile() {
        FileChooser fc = new FileChooser();
        fc.setTitle("Sélectionner un .cbz ou .cbr");
        fc.getExtensionFilters().add(
                new FileChooser.ExtensionFilter("Comic archives", "*.cbz", "*.cbr")
        );
        File f = fc.showOpenDialog(dataDirField.getScene().getWindow());
        if (f == null) return;

        Path inDir = resolve("in");
        try {
            Files.createDirectories(inDir);
            String name = f.getName();
            Path part = inDir.resolve(name + ".part");
            Path fin = inDir.resolve(name);
            Files.copy(f.toPath(), part, StandardCopyOption.REPLACE_EXISTING);
            Files.move(part, fin, StandardCopyOption.REPLACE_EXISTING,
                    StandardCopyOption.ATOMIC_MOVE);
            duplicatesStatusLabel.setText("Déposé : " + fin);
        } catch (IOException ex) {
            duplicatesStatusLabel.setText("Erreur dépôt : " + ex.getMessage());
        }
    }

    // -----------------------------------------------------------------------
    // Helpers privés
    // -----------------------------------------------------------------------

    private void refreshDuplicates() {
        if (services == null) return;
        try {
            List<DupRow> rows = services.getDuplicateService()
                    .listDuplicates(Paths.get(dataDirField.getText()));
            duplicatesTable.getItems().setAll(rows);
            duplicatesStatusLabel.setText("Doublons : " + rows.size());
        } catch (IOException ex) {
            duplicatesStatusLabel.setText("Erreur lecture rapports : " + ex.getMessage());
        }
    }

    private void decide(DupRow row, String action) {
        if (services == null) return;
        try {
            DuplicateDecision decision = DuplicateDecision.valueOf(action);
            services.getDuplicateService()
                    .writeDecision(Paths.get(dataDirField.getText()),
                            row.getJobKey(), decision);
            String key = row.getJobKey();
            duplicatesStatusLabel.setText("Décision : " + action
                    + " (" + key.substring(0, Math.min(12, key.length())) + "...)");
        } catch (Exception ex) {
            duplicatesStatusLabel.setText("Erreur décision : " + ex.getMessage());
        }
    }

    private Path resolve(String sub) {
        return Paths.get(dataDirField.getText()).resolve(sub);
    }

    @SuppressWarnings("unchecked")
    private TableColumn<DupRow, String> buildActionsColumn() {
        TableColumn<DupRow, String> col = new TableColumn<>("Actions");
        col.setCellFactory(tc -> new TableCell<>() {
            private final Button useExisting = new Button("Utiliser existant");
            private final Button discard = new Button("Jeter");
            private final Button force = new Button("Forcer reprocess");
            {
                useExisting.setOnAction(e -> decide(
                        getTableView().getItems().get(getIndex()), "USE_EXISTING_RESULT"));
                discard.setOnAction(e -> decide(
                        getTableView().getItems().get(getIndex()), "DISCARD"));
                force.setOnAction(e -> decide(
                        getTableView().getItems().get(getIndex()), "FORCE_REPROCESS"));
            }
            @Override
            protected void updateItem(String item, boolean empty) {
                super.updateItem(item, empty);
                setGraphic(empty ? null : new HBox(6, useExisting, discard, force));
            }
        });
        return col;
    }
}

