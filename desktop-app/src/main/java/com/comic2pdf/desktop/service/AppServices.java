package com.comic2pdf.desktop.service;

import com.comic2pdf.desktop.client.OrchestratorClient;
import com.comic2pdf.desktop.config.AppConfig;
import com.comic2pdf.desktop.config.ConfigService;
import com.comic2pdf.desktop.service.DuplicateService;

import java.nio.file.Paths;
import java.util.Optional;

/**
 * Conteneur de services de l'application desktop Comic2PDF.
 *
 * <p>Regroupe les services partagés entre les controllers FXML.
 * L'instance est créée dans {@code MainApp.start()} et injectée via setters
 * (sans ServiceLocator singleton).</p>
 */
public class AppServices {

    /** Variable d'environnement pour l'URL de l'orchestrateur. */
    private static final String ENV_URL = "ORCHESTRATOR_URL";

    /** URL par défaut de l'orchestrateur. */
    private static final String DEFAULT_URL = "http://localhost:8080";

    private final OrchestratorClient orchestratorClient;
    private final DuplicateService duplicateService;
    private final ConfigService configService;
    private final String initialDataDir;

    /**
     * Construit un conteneur de services avec les instances fournies.
     *
     * @param orchestratorClient Client HTTP vers l'orchestrateur.
     * @param duplicateService   Service de gestion des doublons.
     * @param configService      Service de persistance de la configuration.
     * @param initialDataDir     Chemin initial du dossier data/.
     */
    public AppServices(OrchestratorClient orchestratorClient,
                       DuplicateService duplicateService,
                       ConfigService configService,
                       String initialDataDir) {
        this.orchestratorClient = orchestratorClient;
        this.duplicateService = duplicateService;
        this.configService = configService;
        this.initialDataDir = initialDataDir;
    }

    /**
     * Crée un conteneur avec les valeurs par défaut pour la production.
     *
     * <p>Séquence d'initialisation :</p>
     * <ol>
     *   <li>Résolution de l'URL orchestrateur depuis {@code ORCHESTRATOR_URL} ou défaut.</li>
     *   <li>Chargement de la config locale via {@link ConfigService#load()} —
     *       la clé API est déjà résolue (env var prioritaire sur config.json).</li>
     *   <li>Injection de la clé API dans {@link OrchestratorClient#setApiKey(String)}.</li>
     * </ol>
     *
     * @return Nouvelle instance {@code AppServices} prête à l'emploi.
     */
    public static AppServices createDefault() {
        String url = Optional.ofNullable(System.getenv(ENV_URL))
                .filter(s -> !s.isBlank())
                .orElse(DEFAULT_URL);

        ConfigService configService = new ConfigService();
        AppConfig cfg = configService.load();

        // Utiliser l'URL depuis la config si elle y est stockée et non vide
        String resolvedUrl = (cfg.getOrchestratorUrl() != null && !cfg.getOrchestratorUrl().isBlank())
                ? cfg.getOrchestratorUrl()
                : url;
        // Mais env var ORCHESTRATOR_URL reste prioritaire sur config.json
        if (System.getenv(ENV_URL) != null && !System.getenv(ENV_URL).isBlank()) {
            resolvedUrl = url;
        }

        OrchestratorClient client = new OrchestratorClient(resolvedUrl);
        // Injecter la clé API résolue (env var déjà prioritaire via ConfigService.load())
        client.setApiKey(cfg.getApiKey());

        return new AppServices(
                client,
                new DuplicateService(),
                configService,
                Paths.get("..", "data").normalize().toString()
        );
    }

    /**
     * @return Client HTTP vers l'orchestrateur.
     */
    public OrchestratorClient getOrchestratorClient() {
        return orchestratorClient;
    }

    /**
     * @return Service de gestion des doublons.
     */
    public DuplicateService getDuplicateService() {
        return duplicateService;
    }

    /**
     * @return Service de persistance de la configuration locale.
     */
    public ConfigService getConfigService() {
        return configService;
    }

    /**
     * @return Chemin initial du dossier data/.
     */
    public String getInitialDataDir() {
        return initialDataDir;
    }
}

