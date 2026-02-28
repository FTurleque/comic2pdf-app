package com.fturleque.comic2pdf.desktop.ui;

import com.fturleque.comic2pdf.desktop.JobsView;
import com.fturleque.comic2pdf.desktop.MainView;
import com.fturleque.comic2pdf.desktop.OrchestratorClient;
import com.fturleque.comic2pdf.desktop.config.ConfigService;
import com.fturleque.comic2pdf.desktop.config.ConfigView;
import javafx.application.Application;
import javafx.scene.Scene;
import javafx.scene.control.Tab;
import javafx.scene.control.TabPane;
import javafx.scene.control.TextField;
import javafx.stage.Stage;

import java.nio.file.Path;
import java.nio.file.Paths;

/**
 * Application JavaFX dédiée aux tests UI (TestFX).
 *
 * <p>TestFX instancie {@link Application} via reflection, sans possibilité de passer
 * des arguments au constructeur. L'injection se fait via des champs statiques nullable :</p>
 * <ul>
 *   <li>{@link #dataDirOverride} : dossier data/ injecté (pour les tests doublons)</li>
 *   <li>{@link #orchestratorUrlOverride} : URL de l'orchestrateur (pour les stubs HTTP)</li>
 *   <li>{@link #jobsAutoRefreshOverride} : désactiver le poll réseau automatique en test</li>
 * </ul>
 *
 * <p>Pattern d'utilisation dans chaque test :</p>
 * <pre>{@code
 * @BeforeEach void setup() {
 *     TestableMainApp.orchestratorUrlOverride = "http://localhost:" + stubPort;
 *     TestableMainApp.jobsAutoRefreshOverride = false;
 * }
 * @AfterEach void tearDown() { TestableMainApp.resetOverrides(); }
 * }</pre>
 *
 * <p>Fallback sur les valeurs par défaut si un champ est null — aucun NPE possible.</p>
 */
public class TestableMainApp extends Application {

    /** Surcharge du dossier data/ (pour les tests de doublons). {@code null} = "../data". */
    public static Path dataDirOverride = null;

    /** Surcharge de l'URL orchestrateur (pour les stubs HTTP). {@code null} = <code>http://localhost:8080</code>. */
    public static String orchestratorUrlOverride = null;

    /**
     * Surcharge du flag autoRefresh de JobsView.
     * {@code false} = pas de poll réseau (essentiel pour les tests).
     * {@code null} = true (comportement production).
     */
    public static Boolean jobsAutoRefreshOverride = null;

    /** Référence à la JobsView créée — permet d'appeler {@code forceRefresh()} depuis les tests. */
    public static JobsView lastJobsView;

    /**
     * Réinitialise tous les overrides à leur état par défaut ({@code null}).
     * Doit être appelé dans {@code @AfterEach} de chaque test UI.
     */
    public static void resetOverrides() {
        dataDirOverride = null;
        orchestratorUrlOverride = null;
        jobsAutoRefreshOverride = null;
        lastJobsView = null;
    }

    @Override
    public void start(Stage stage) {
        // Résolution de l'URL orchestrateur : override ou fallback
        String url = orchestratorUrlOverride != null
                ? orchestratorUrlOverride
                : "http://localhost:8080";
        OrchestratorClient client = new OrchestratorClient(url);

        // Résolution du dossier data/ : override (Path → String) ou fallback
        String dataDir = dataDirOverride != null
                ? dataDirOverride.toString()
                : Paths.get("..", "data").normalize().toString();
        MainView mainView = new MainView(dataDir);
        TextField dataDirField = mainView.getDataDirField();

        // JobsView avec autoRefresh contrôlable (false en test pour éviter tout poll réseau)
        boolean autoRefresh = jobsAutoRefreshOverride != null
                ? jobsAutoRefreshOverride
                : true;
        JobsView jobsView = new JobsView(client, dataDirField, autoRefresh);
        lastJobsView = jobsView;

        // ConfigService en mode test : crée une config locale avec l'URL du stub
        // pour que ConfigView.loadConfig() remplisse urlField avec l'URL du stub.
        // Ainsi applyConfig() enverra le POST au bon endpoint.
        ConfigService configService = new ConfigService();
        try {
            com.fturleque.comic2pdf.desktop.config.AppConfig preloadedCfg =
                    new com.fturleque.comic2pdf.desktop.config.AppConfig();
            preloadedCfg.setOrchestratorUrl(url);
            configService.save(preloadedCfg);
        } catch (Exception ignored) {
            // Si la sauvegarde échoue (ex: pas d'accès AppData en test), on continue
        }
        ConfigView configView = new ConfigView(configService, client);

        // Onglets avec IDs stables identiques à MainApp (pour réutiliser les mêmes lookups)
        Tab tabDuplicates = new Tab("Doublons", mainView);
        tabDuplicates.setClosable(false);
        tabDuplicates.setId("tabDuplicates");

        Tab tabJobs = new Tab("Jobs", jobsView);
        tabJobs.setClosable(false);
        tabJobs.setId("tabJobs");

        Tab tabConfig = new Tab("Configuration", configView);
        tabConfig.setClosable(false);
        tabConfig.setId("tabConfig");

        TabPane tabPane = new TabPane(tabDuplicates, tabJobs, tabConfig);
        tabPane.setId("mainTabs");

        Scene scene = new Scene(tabPane, 1100, 700);
        stage.setTitle("Comic2PDF - Desktop [TEST]");
        stage.setScene(scene);
        stage.setOnCloseRequest(e -> jobsView.stop());
        stage.show();
    }
}

