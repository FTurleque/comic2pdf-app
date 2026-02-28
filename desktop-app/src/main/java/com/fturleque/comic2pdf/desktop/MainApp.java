package com.fturleque.comic2pdf.desktop;

import com.fturleque.comic2pdf.desktop.config.ConfigService;
import com.fturleque.comic2pdf.desktop.config.ConfigView;
import javafx.application.Application;
import javafx.scene.Scene;
import javafx.scene.control.Tab;
import javafx.scene.control.TabPane;
import javafx.scene.control.TextField;
import javafx.stage.Stage;

/**
 * Point d'entrée de l'application desktop Comic2PDF.
 *
 * <p>Interface organisée en 3 onglets :</p>
 * <ul>
 *   <li><b>Doublons</b> : gestion des fichiers en attente de décision.</li>
 *   <li><b>Jobs</b>     : suivi temps-réel des jobs de l'orchestrateur.</li>
 *   <li><b>Configuration</b> : paramètres de l'application et de l'orchestrateur.</li>
 * </ul>
 */
public class MainApp extends Application {

    private JobsView jobsView;

    @Override
    public void start(Stage stage) {
        // Client orchestrateur partagé entre Jobs + Config
        var client = new OrchestratorClient();

        // Vue principale Doublons (existante) — partage le champ dataDirField
        var mainView = new MainView();

        // Référence partagée vers le champ dataDirField de MainView
        // (nécessaire pour que JobsView ouvre le bon dossier data/out/)
        TextField dataDirField = mainView.getDataDirField();

        // Vue Jobs
        jobsView = new JobsView(client, dataDirField);

        // Vue Configuration
        var configService = new ConfigService();
        var configView = new ConfigView(configService, client);

        // TabPane
        var tabDuplicates = new Tab("Doublons", mainView);
        tabDuplicates.setClosable(false);

        var tabJobs = new Tab("Jobs", jobsView);
        tabJobs.setClosable(false);

        var tabConfig = new Tab("Configuration", configView);
        tabConfig.setClosable(false);

        var tabPane = new TabPane(tabDuplicates, tabJobs, tabConfig);

        var scene = new Scene(tabPane, 1100, 700);
        stage.setTitle("Comic2PDF - Desktop");
        stage.setScene(scene);
        stage.setOnCloseRequest(e -> {
            if (jobsView != null) jobsView.stop();
        });
        stage.show();
    }

    /**
     * Point d'entrée Java.
     *
     * @param args Arguments de la ligne de commande (ignorés).
     */
    public static void main(String[] args) {
        launch(args);
    }
}
