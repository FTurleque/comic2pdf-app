package com.comic2pdf.desktop.ui.controller;

import com.comic2pdf.desktop.config.AppConfig;
import com.comic2pdf.desktop.service.AppServices;
import javafx.fxml.FXML;
import javafx.scene.control.Label;
import javafx.scene.control.PasswordField;
import javafx.scene.control.Spinner;
import javafx.scene.control.SpinnerValueFactory;
import javafx.scene.control.TextField;

/**
 * Controller de l'onglet Configuration.
 *
 * <p>Charge la configuration locale via {@code ConfigService} lors de l'injection
 * des services et envoie un {@code POST /config} à l'orchestrateur via
 * {@code OrchestratorClient} lorsque l'utilisateur clique "Appliquer".</p>
 *
 * <h2>Gestion de la clé API</h2>
 * <ul>
 *   <li>Si {@code ORCHESTRATOR_API_KEY} est définie (env var), le champ est désactivé
 *       et un label indique la source — la valeur n'est jamais pré-remplie visuellement.</li>
 *   <li>Sinon, l'utilisateur peut saisir la clé dans un {@link PasswordField} (caractères masqués).</li>
 *   <li>La clé n'est jamais loguée.</li>
 * </ul>
 */
public class ConfigController {

    private static final String ENV_API_KEY = "ORCHESTRATOR_API_KEY";

    @FXML private TextField orchestratorUrlField;
    @FXML private Spinner<Integer> prepConcurrencySpinner;
    @FXML private Spinner<Integer> ocrConcurrencySpinner;
    @FXML private Spinner<Integer> timeoutSecondsSpinner;
    @FXML private TextField defaultOcrLangField;
    @FXML private PasswordField apiKeyField;
    @FXML private Label apiKeySourceLabel;
    @FXML private Label configStatusLabel;

    private AppServices services;

    /**
     * Initialisation FXML : configure les {@link SpinnerValueFactory} avec les plages valides.
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
        // Mettre à jour la clé API dans le client seulement si l'env var n'est pas active
        if (!isApiKeyFromEnv()) {
            services.getOrchestratorClient().setApiKey(cfg.getApiKey());
        }
        boolean ok = services.getOrchestratorClient().postConfig(cfg);
        configStatusLabel.setText(ok
                ? "Configuration appliquée avec succès."
                : "Sauvegardée localement (orchestrateur non disponible ou accès refusé).");
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

        // Gestion du champ clé API
        if (isApiKeyFromEnv()) {
            // Clé depuis env var : désactiver le champ + indiquer la source
            apiKeyField.setDisable(true);
            apiKeyField.setText(""); // ne jamais pré-remplir depuis l'env
            apiKeyField.setPromptText("Configurée via ORCHESTRATOR_API_KEY (env)");
            if (apiKeySourceLabel != null) {
                apiKeySourceLabel.setText("⚠ Clé active depuis la variable d'environnement ORCHESTRATOR_API_KEY");
            }
        } else {
            apiKeyField.setDisable(false);
            // Pré-remplir depuis config.json uniquement si non vide
            String storedKey = cfg.getApiKey();
            if (storedKey != null && !storedKey.isBlank()) {
                apiKeyField.setText(storedKey);
            } else {
                apiKeyField.setText("");
            }
            if (apiKeySourceLabel != null) {
                apiKeySourceLabel.setText("");
            }
        }
        configStatusLabel.setText("Configuration chargée.");
    }

    private AppConfig buildConfigFromUi() {
        AppConfig cfg = new AppConfig();
        cfg.setOrchestratorUrl(orchestratorUrlField.getText().trim());
        cfg.setPrepConcurrency(prepConcurrencySpinner.getValue());
        cfg.setOcrConcurrency(ocrConcurrencySpinner.getValue());
        cfg.setJobTimeoutSeconds(timeoutSecondsSpinner.getValue());
        cfg.setDefaultOcrLang(defaultOcrLangField.getText().trim());
        // Clé API : utiliser le champ seulement si l'env var n'est pas active
        if (!isApiKeyFromEnv()) {
            cfg.setApiKey(apiKeyField.getText());
        } else {
            // Conserver la clé depuis l'env var (déjà résolue dans ConfigService.load())
            cfg.setApiKey(System.getenv(ENV_API_KEY));
        }
        return cfg;
    }

    /**
     * Vérifie si la clé API est fournie via la variable d'environnement {@code ORCHESTRATOR_API_KEY}.
     *
     * @return {@code true} si l'env var est définie et non vide.
     */
    private static boolean isApiKeyFromEnv() {
        String envKey = System.getenv(ENV_API_KEY);
        return envKey != null && !envKey.isBlank();
    }
}

