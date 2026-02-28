package com.comic2pdf.desktop.ui;

import com.comic2pdf.desktop.OrchestratorClient;
import com.comic2pdf.desktop.config.AppConfig;
import com.comic2pdf.desktop.config.ConfigService;
import com.comic2pdf.desktop.duplicates.DuplicateService;
import com.comic2pdf.desktop.service.AppServices;
import com.comic2pdf.desktop.ui.controller.MainController;
import javafx.application.Application;
import javafx.fxml.FXMLLoader;
import javafx.scene.Parent;
import javafx.scene.Scene;
import javafx.stage.Stage;

import java.net.URL;
import java.nio.file.Path;
import java.nio.file.Paths;

/**
 * Application JavaFX dédiée aux tests UI (TestFX).
 *
 * <p>Charge le même {@code MainView.fxml} que la production et injecte
 * les overrides de test via les setters des controllers.</p>
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
 * @BeforeAll static void setup() {
 *     TestableMainApp.orchestratorUrlOverride = "http://localhost:" + stubPort;
 *     TestableMainApp.jobsAutoRefreshOverride = false;
 * }
 * @AfterAll static void tearDown() { TestableMainApp.resetOverrides(); }
 * }</pre>
 */
public class TestableMainApp extends Application {

    /** Surcharge du dossier data/ (pour les tests de doublons). {@code null} = "../data". */
    public static Path dataDirOverride = null;

    /** Surcharge de l'URL orchestrateur (pour les stubs HTTP). {@code null} = défaut. */
    public static String orchestratorUrlOverride = null;

    /**
     * Surcharge du flag autoRefresh de JobsController.
     * {@code false} = pas de poll réseau (essentiel pour les tests).
     * {@code null} = true (comportement production).
     */
    public static Boolean jobsAutoRefreshOverride = null;

    /**
     * Réinitialise tous les overrides à {@code null}.
     * Doit être appelé dans {@code @AfterAll} de chaque test UI.
     */
    public static void resetOverrides() {
        dataDirOverride = null;
        orchestratorUrlOverride = null;
        jobsAutoRefreshOverride = null;
    }

    @Override
    public void start(Stage stage) throws Exception {
        String url = orchestratorUrlOverride != null
                ? orchestratorUrlOverride : "http://localhost:8080";
        String dataDir = dataDirOverride != null
                ? dataDirOverride.toString()
                : Paths.get("..", "data").normalize().toString();
        boolean autoRefresh = jobsAutoRefreshOverride != null
                ? jobsAutoRefreshOverride : true;

        // Pré-charger la config avec l'URL du stub pour que ConfigController.loadConfig()
        // remplisse orchestratorUrlField avec la bonne URL (requis par ConfigUiTest).
        ConfigService configService = new ConfigService();
        try {
            AppConfig cfg = new AppConfig();
            cfg.setOrchestratorUrl(url);
            configService.save(cfg);
        } catch (Exception ignored) {
            // Si la sauvegarde échoue (ex: pas d'accès AppData en test), on continue
        }

        AppServices services = new AppServices(
                new OrchestratorClient(url),
                new DuplicateService(),
                configService,
                dataDir
        );

        URL fxmlUrl = getClass().getResource("/fxml/MainView.fxml");
        if (fxmlUrl == null) {
            throw new IllegalStateException("FXML introuvable : /fxml/MainView.fxml");
        }
        FXMLLoader loader = new FXMLLoader(fxmlUrl);
        Parent root = loader.load();

        MainController ctrl = loader.getController();
        // ORDRE IMPORTANT : setJobsAutoRefresh AVANT setServices
        // (le polling démarre dans setServices si autoRefresh=true)
        ctrl.setJobsAutoRefresh(autoRefresh);
        ctrl.setServices(services);
        ctrl.setInitialDataDir(dataDir);

        Scene scene = new Scene(root, 1100, 700);
        stage.setTitle("Comic2PDF - Desktop [TEST]");
        stage.setScene(scene);
        stage.show();
    }
}

