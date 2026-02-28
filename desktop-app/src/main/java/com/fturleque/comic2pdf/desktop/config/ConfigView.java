package com.fturleque.comic2pdf.desktop.config;

import com.fturleque.comic2pdf.desktop.OrchestratorClient;
import javafx.geometry.Insets;
import javafx.scene.control.*;
import javafx.scene.layout.*;

/**
 * Vue JavaFX de configuration de l'application.
 *
 * <p>Permet de modifier :</p>
 * <ul>
 *   <li>URL de l'orchestrateur</li>
 *   <li>PREP_CONCURRENCY</li>
 *   <li>OCR_CONCURRENCY</li>
 *   <li>Timeout job (secondes)</li>
 *   <li>Langue OCR par défaut</li>
 * </ul>
 *
 * <p>Bouton "Appliquer" : sauvegarde locale + POST /config sur l'orchestrateur.</p>
 */
public class ConfigView extends VBox {

    private final ConfigService configService;
    private final OrchestratorClient client;

    private final TextField urlField = new TextField();
    private final Spinner<Integer> prepConcurrencySpinner = new Spinner<>(1, 16, 2);
    private final Spinner<Integer> ocrConcurrencySpinner = new Spinner<>(1, 8, 1);
    private final Spinner<Integer> timeoutSpinner = new Spinner<>(60, 7200, 600, 60);
    private final TextField ocrLangField = new TextField();
    private final Label statusLabel = new Label();

    /**
     * Construit la vue Configuration.
     *
     * @param configService Service de persistance locale de la configuration.
     * @param client        Client HTTP vers l'orchestrateur.
     */
    public ConfigView(ConfigService configService, OrchestratorClient client) {
        this.configService = configService;
        this.client = client;
        setPadding(new Insets(16));
        setSpacing(12);
        buildUi();
        loadConfig();
    }

    private void buildUi() {
        prepConcurrencySpinner.setEditable(true);
        ocrConcurrencySpinner.setEditable(true);
        timeoutSpinner.setEditable(true);

        var grid = new GridPane();
        grid.setHgap(12);
        grid.setVgap(8);

        int row = 0;
        grid.add(new Label("URL orchestrateur :"), 0, row);
        grid.add(urlField, 1, row++);

        grid.add(new Label("PREP_CONCURRENCY :"), 0, row);
        grid.add(prepConcurrencySpinner, 1, row++);

        grid.add(new Label("OCR_CONCURRENCY :"), 0, row);
        grid.add(ocrConcurrencySpinner, 1, row++);

        grid.add(new Label("Timeout job (s) :"), 0, row);
        grid.add(timeoutSpinner, 1, row++);

        grid.add(new Label("Langue OCR :"), 0, row);
        grid.add(ocrLangField, 1, row++);

        var applyBtn = new Button("Appliquer");
        applyBtn.setDefaultButton(true);
        applyBtn.setOnAction(e -> applyConfig());

        var resetBtn = new Button("Recharger");
        resetBtn.setOnAction(e -> loadConfig());

        var btnRow = new HBox(8, applyBtn, resetBtn);

        getChildren().addAll(
                new Label("Configuration"),
                new Separator(),
                grid,
                btnRow,
                statusLabel
        );
    }

    /**
     * Charge la configuration depuis le disque et remplit les champs UI.
     */
    private void loadConfig() {
        AppConfig cfg = configService.load();
        urlField.setText(cfg.getOrchestratorUrl());
        prepConcurrencySpinner.getValueFactory().setValue(cfg.getPrepConcurrency());
        ocrConcurrencySpinner.getValueFactory().setValue(cfg.getOcrConcurrency());
        timeoutSpinner.getValueFactory().setValue(cfg.getJobTimeoutSeconds());
        ocrLangField.setText(cfg.getDefaultOcrLang());
        statusLabel.setText("Configuration chargée.");
    }

    /**
     * Sauvegarde la configuration et l'envoie à l'orchestrateur.
     */
    private void applyConfig() {
        AppConfig cfg = buildConfigFromUi();
        try {
            configService.save(cfg);
        } catch (Exception e) {
            statusLabel.setText("Erreur sauvegarde : " + e.getMessage());
            return;
        }

        // Mettre à jour l'URL du client si elle a changé
        client.setBaseUrl(cfg.getOrchestratorUrl());

        boolean ok = client.postConfig(cfg);
        if (ok) {
            statusLabel.setText("Configuration appliquée avec succès.");
        } else {
            statusLabel.setText("Sauvegardée localement (orchestrateur non disponible).");
        }
    }

    /**
     * Construit un {@link AppConfig} depuis les valeurs actuelles de l'UI.
     *
     * @return Config construite.
     */
    private AppConfig buildConfigFromUi() {
        AppConfig cfg = new AppConfig();
        cfg.setOrchestratorUrl(urlField.getText().trim());
        cfg.setPrepConcurrency(prepConcurrencySpinner.getValue());
        cfg.setOcrConcurrency(ocrConcurrencySpinner.getValue());
        cfg.setJobTimeoutSeconds(timeoutSpinner.getValue());
        cfg.setDefaultOcrLang(ocrLangField.getText().trim());
        return cfg;
    }

    /**
     * Retourne la configuration actuellement affichée dans l'UI (sans sauvegarder).
     * Utile pour les tests.
     *
     * @return {@link AppConfig} construite depuis l'UI.
     */
    public AppConfig getCurrentConfigFromUi() {
        return buildConfigFromUi();
    }
}

