package com.comic2pdf.desktop.util;

import javafx.scene.control.Alert;

import java.awt.Desktop;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;

/**
 * Utilitaires UI JavaFX partagés entre les controllers.
 *
 * <p>Classe utilitaire non instanciable — méthodes statiques uniquement.</p>
 */
public final class FxUtils {

    /** Constructeur privé — classe utilitaire non instanciable. */
    private FxUtils() {}

    /**
     * Ouvre un dossier dans l'explorateur système.
     * Crée le dossier s'il est absent. Silencieux si Desktop non supporté.
     *
     * @param dir Chemin du dossier à ouvrir.
     * @return {@code true} si l'ouverture a réussi, {@code false} sinon.
     */
    public static boolean openDirectory(Path dir) {
        try {
            Files.createDirectories(dir);
            if (Desktop.isDesktopSupported()
                    && Desktop.getDesktop().isSupported(Desktop.Action.OPEN)) {
                Desktop.getDesktop().open(dir.toFile());
                return true;
            }
        } catch (IOException ignored) {
            // Silencieux — l'appelant affiche un message si nécessaire
        }
        return false;
    }

    /**
     * Affiche une alerte d'erreur JavaFX.
     *
     * @param titre   Titre de la fenêtre d'alerte.
     * @param message Message d'erreur.
     */
    public static void showError(String titre, String message) {
        Alert alert = new Alert(Alert.AlertType.ERROR);
        alert.setTitle(titre);
        alert.setHeaderText(null);
        alert.setContentText(message);
        alert.showAndWait();
    }

    /**
     * Affiche une alerte d'information JavaFX.
     *
     * @param titre   Titre de la fenêtre.
     * @param message Message d'information.
     */
    public static void showInfo(String titre, String message) {
        Alert alert = new Alert(Alert.AlertType.INFORMATION);
        alert.setTitle(titre);
        alert.setHeaderText(null);
        alert.setContentText(message);
        alert.showAndWait();
    }
}

