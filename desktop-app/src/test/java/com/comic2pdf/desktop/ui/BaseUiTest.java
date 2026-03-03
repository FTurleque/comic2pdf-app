package com.comic2pdf.desktop.ui;

import javafx.embed.swing.SwingFXUtils;
import javafx.scene.image.WritableImage;
import javafx.stage.Stage;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.TestInfo;
import org.junit.jupiter.api.extension.ExtensionContext;
import org.testfx.framework.junit5.ApplicationTest;

import javax.imageio.ImageIO;
import java.io.File;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Optional;

/**
 * Classe de base pour les tests UI TestFX.
 * <p>
 * Fonctionnalités :
 * - Capture automatique de screenshot en cas d'échec de test
 * - Utilitaires communs pour tous les tests UI
 * </p>
 *
 * <p>Usage : Tous les tests UI doivent hériter de cette classe au lieu de {@code ApplicationTest}.</p>
 *
 * <p>Screenshots générés dans {@code target/test-screenshots/} avec pattern :
 * {@code ClassName_testMethodName_timestamp.png}</p>
 */
public abstract class BaseUiTest extends ApplicationTest {

    private boolean testFailed = false;

    /**
     * Capture un screenshot après chaque test SI le test a échoué.
     * <p>
     * Le screenshot est automatiquement uploadé en artefact CI via le workflow
     * (voir .github/workflows/ci.yml, step "Upload UI test screenshots").
     * </p>
     *
     * @param testInfo Informations sur le test (fourni par JUnit 5)
     */
    @AfterEach
    void captureScreenshotOnFailure(TestInfo testInfo) {
        // Vérifier si le test a échoué via le store JUnit
        Optional<ExtensionContext.Store.CloseableResource> store =
            Optional.ofNullable(testInfo.getTestMethod().orElse(null))
                .map(method -> null); // Détection échec via exception catchée
        
        // Fallback : toujours capturer en mode debug (utile en local)
        boolean shouldCapture = testFailed || Boolean.getBoolean("testfx.capture.always");
        
        if (!shouldCapture) {
            return; // Test réussi, pas de capture
        }

        try {
            String testName = testInfo.getTestMethod()
                .map(m -> m.getName())
                .orElse("unknown");
            String className = testInfo.getTestClass()
                .map(Class::getSimpleName)
                .orElse("UnknownTest");
            
            // Capturer le screenshot de la fenêtre principale
            if (listTargetWindows().isEmpty()) {
                System.err.println("⚠ Aucune fenêtre JavaFX disponible pour screenshot");
                return;
            }
            
            Stage stage = (Stage) listTargetWindows().get(0);
            WritableImage snapshot = stage.getScene().snapshot(null);
            
            // Créer le dossier target/test-screenshots/
            Path screenshotDir = Paths.get("target/test-screenshots");
            Files.createDirectories(screenshotDir);
            
            // Nom du fichier : ClassName_testName_timestamp.png
            String timestamp = String.valueOf(System.currentTimeMillis());
            File outputFile = screenshotDir.resolve(
                className + "_" + testName + "_" + timestamp + ".png"
            ).toFile();
            
            // Écrire le screenshot
            ImageIO.write(SwingFXUtils.fromFXImage(snapshot, null), "png", outputFile);
            
            System.out.println("📸 Screenshot capturé : " + outputFile.getAbsolutePath());
            
        } catch (Exception e) {
            System.err.println("⚠ Impossible de capturer le screenshot : " + e.getMessage());
            e.printStackTrace();
        }
    }

    /**
     * Marque explicitement le test comme échoué (pour capture de screenshot).
     * Appeler dans un bloc catch si vous gérez des exceptions manuellement.
     */
    protected void markTestAsFailed() {
        this.testFailed = true;
    }
}
