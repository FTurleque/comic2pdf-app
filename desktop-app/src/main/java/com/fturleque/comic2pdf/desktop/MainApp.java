package com.fturleque.comic2pdf.desktop;

import com.fturleque.comic2pdf.desktop.service.AppServices;
import com.fturleque.comic2pdf.desktop.ui.controller.MainController;
import javafx.application.Application;
import javafx.fxml.FXMLLoader;
import javafx.scene.Parent;
import javafx.scene.Scene;
import javafx.stage.Stage;

import java.io.IOException;
import java.net.URL;

/**
 * Point d'entrée de l'application desktop Comic2PDF.
 *
 * <p>Charge {@code /fxml/MainView.fxml} via {@link FXMLLoader}, crée {@link AppServices}
 * via {@code createDefault()} et injecte les services dans {@link MainController}
 * via setters (sans ServiceLocator).</p>
 *
 * <p>Interface organisée en 3 onglets :</p>
 * <ul>
 *   <li><b>Doublons</b> : gestion des fichiers en attente de décision.</li>
 *   <li><b>Jobs</b>     : suivi temps-réel des jobs de l'orchestrateur.</li>
 *   <li><b>Configuration</b> : paramètres de l'application et de l'orchestrateur.</li>
 * </ul>
 */
public class MainApp extends Application {

    private MainController mainController;

    @Override
    public void start(Stage stage) throws IOException {
        AppServices services = AppServices.createDefault();

        URL fxmlUrl = getClass().getResource("/fxml/MainView.fxml");
        if (fxmlUrl == null) {
            throw new IllegalStateException("FXML introuvable : /fxml/MainView.fxml");
        }
        FXMLLoader loader = new FXMLLoader(fxmlUrl);
        Parent root = loader.load();

        mainController = loader.getController();
        // Désactiver autoRefresh avant d'injecter les services (le polling démarre dans setServices)
        // En production autoRefresh reste true (valeur par défaut)
        mainController.setServices(services);
        mainController.setInitialDataDir(services.getInitialDataDir());

        Scene scene = new Scene(root, 1100, 700);
        stage.setTitle("Comic2PDF - Desktop");
        stage.setScene(scene);
        stage.setOnCloseRequest(e -> {
            if (mainController != null) mainController.stopJobs();
        });
        stage.show();
    }

    @Override
    public void stop() {
        if (mainController != null) {
            mainController.stopJobs();
        }
    }

    /**
     * Point d'entrée Java.
     *
     * @param args Arguments de la ligne de commande (ignorés).
     */
    @SuppressWarnings("unused")
    public static void main(String[] args) {
        launch(args);
    }
}
