package com.comic2pdf.desktop.ui.controller;

import com.comic2pdf.desktop.config.AppConfig;
import com.comic2pdf.desktop.service.AppServices;
import javafx.fxml.FXML;
import javafx.scene.control.Label;
import javafx.scene.control.Spinner;
import javafx.scene.control.SpinnerValueFactory;
import javafx.scene.control.TextField;

/**
 * Controller de l'onglet Configuration.
 *
 * <p>Charge la configuration locale via {@code ConfigService} lors de l'injection
 * des services et envoie un {@code POST /config} à l'orchestrateur via
 * {@code OrchestratorClient} lorsque l'utilisateur clique "Appliquer".</p>
 */
public class ConfigController {

    @FXML private TextField orchestratorUrlField;
    @FXML private Spinner<Integer> prepConcurrencySpinner;
    @FXML private Spinner<Integer> ocrConcurrencySpinner;
    @FXML private Spinner<Integer> timeoutSecondsSpinner;
    @FXML private TextField defaultOcrLangField;
    @FXML private Label configStatusLabel;

    private AppServices services;

    /**
     * Initialisation FXML : configure les {@link SpinnerValueFactory} avec les plages valides.
     * Les valeurs par défaut seront écrasées par {@link #loadConfig()} lors de {@link #setServices}.
     */
    @FXML
    public void initialize() {
        prepConcurrencySpinner.setValueFactory(
                new SpinnerValueFactory.IntegerSpinnerValueFactory(1, 16, 2));
        prepConcurrencySpinner.setEditable(true);

        ocrConcurrencySpinner.setValueFactory(
                new SpinnerValueFactory.IntegerSpinnerValueFactory(1, 8, 1));
        ocrConcurrencySpinner.setEditable(true);

        timeoutSecondsSpinner.setValueFactory(
                new SpinnerValueFactory.IntegerSpinnerValueFactory(60, 7200, 600, 60));
        timeoutSecondsSpinner.setEditable(true);
    }

    /**
     * Injecte le conteneur de services et charge la configuration persistée.
     *
     * @param services Services partagés de l'application.
     */
    public void setServices(AppServices services) {
        this.services = services;
        loadConfig();
    }

    /**
     * Sauvegarde la configuration et l'envoie à l'orchestrateur via {@code POST /config}.
     */
    @FXML
    public void onApplyConfig() {
        if (services == null) return;
        AppConfig cfg = buildConfigFromUi();
        try {
            services.getConfigService().save(cfg);
        } catch (Exception ex) {
            configStatusLabel.setText("Erreur sauvegarde : " + ex.getMessage());
            return;
        }
        services.getOrchestratorClient().setBaseUrl(cfg.getOrchestratorUrl());
        boolean ok = services.getOrchestratorClient().postConfig(cfg);
        configStatusLabel.setText(ok
                ? "Configuration appliquée avec succès."
                : "Sauvegardée localement (orchestrateur non disponible).");
    }

    /** Recharge la configuration depuis le disque. */
    @FXML
    public void onReloadConfig() {
        loadConfig();
    }

    // -----------------------------------------------------------------------
    // Helpers privés
    // -----------------------------------------------------------------------

    private void loadConfig() {
        if (services == null) return;
        AppConfig cfg = services.getConfigService().load();
        orchestratorUrlField.setText(cfg.getOrchestratorUrl());
        prepConcurrencySpinner.getValueFactory().setValue(cfg.getPrepConcurrency());
        ocrConcurrencySpinner.getValueFactory().setValue(cfg.getOcrConcurrency());
        timeoutSecondsSpinner.getValueFactory().setValue(cfg.getJobTimeoutSeconds());
        defaultOcrLangField.setText(cfg.getDefaultOcrLang());
        configStatusLabel.setText("Configuration chargée.");
    }

    private AppConfig buildConfigFromUi() {
        AppConfig cfg = new AppConfig();
        cfg.setOrchestratorUrl(orchestratorUrlField.getText().trim());
        cfg.setPrepConcurrency(prepConcurrencySpinner.getValue());
        cfg.setOcrConcurrency(ocrConcurrencySpinner.getValue());
        cfg.setJobTimeoutSeconds(timeoutSecondsSpinner.getValue());
        cfg.setDefaultOcrLang(defaultOcrLangField.getText().trim());
        return cfg;
    }
}

