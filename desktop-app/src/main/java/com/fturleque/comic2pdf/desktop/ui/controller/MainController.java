package com.fturleque.comic2pdf.desktop.ui.controller;

import com.fturleque.comic2pdf.desktop.service.AppServices;
import javafx.fxml.FXML;
import javafx.scene.control.TabPane;

/**
 * Controller principal de la fenêtre Comic2PDF.
 *
 * <p>Charge les 3 onglets via {@code <fx:include>} FXML et délègue l'injection
 * des services aux controllers fils.</p>
 *
 * <p>Convention JavaFX : {@code <fx:include fx:id="duplicatesView">} génère
 * automatiquement le champ {@code @FXML DuplicatesController duplicatesViewController}
 * (suffixe "Controller" automatique du FXMLLoader).</p>
 */
public class MainController {

    @FXML private TabPane mainTabs;
    @FXML private DuplicatesController duplicatesViewController;
    @FXML private JobsController jobsViewController;
    @FXML private ConfigController configViewController;

    /**
     * Injecte le conteneur de services dans tous les controllers fils.
     * Doit être appelé APRÈS {@link #setJobsAutoRefresh(boolean)}.
     *
     * @param services Conteneur de services partagés.
     */
    public void setServices(AppServices services) {
        duplicatesViewController.setServices(services);
        jobsViewController.setServices(services);
        configViewController.setServices(services);
    }

    /**
     * Active ou désactive le polling automatique des jobs.
     * Doit être appelé AVANT {@link #setServices(AppServices)}.
     *
     * @param autoRefresh {@code false} pour désactiver le polling (utile en tests).
     */
    public void setJobsAutoRefresh(boolean autoRefresh) {
        jobsViewController.setAutoRefresh(autoRefresh);
    }

    /**
     * Définit le chemin initial du dossier data/ dans l'onglet Doublons.
     *
     * @param dataDir Chemin du dossier data/.
     */
    public void setInitialDataDir(String dataDir) {
        duplicatesViewController.setInitialDataDir(dataDir);
    }

    /**
     * Arrête le service de polling des jobs.
     * Doit être appelé lors de la fermeture de la fenêtre.
     */
    public void stopJobs() {
        if (jobsViewController != null) {
            jobsViewController.stop();
        }
    }
}

