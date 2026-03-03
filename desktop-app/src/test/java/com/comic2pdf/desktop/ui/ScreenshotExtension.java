package com.comic2pdf.desktop.ui;

import javafx.application.Platform;
import javafx.embed.swing.SwingFXUtils;
import javafx.stage.Stage;
import javafx.stage.Window;
import org.junit.jupiter.api.extension.ExtensionContext;
import org.junit.jupiter.api.extension.TestExecutionExceptionHandler;

import javax.imageio.ImageIO;
import java.io.File;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

/**
 * Extension JUnit 5 — capture automatique de screenshot en cas d'échec de test UI.
 *
 * <p>Enregistrée via {@code @ExtendWith(ScreenshotExtension.class)} sur {@link BaseUiTest},
 * cette extension est héritée automatiquement par toutes les sous-classes sans aucune
 * modification requise dans les tests existants.</p>
 *
 * <h2>Mécanisme de capture</h2>
 * <ol>
 *   <li>Le handler JUnit s'exécute sur le thread de test (non-FX).</li>
 *   <li>Un {@code CompletableFuture} est créé et la capture est déléguée au FX Application
 *       Thread via {@code Platform.runLater}.</li>
 *   <li>Dans le {@code Platform.runLater} : copie défensive obligatoire
 *       {@code new ArrayList<>(Window.getWindows())} — on n'itère jamais directement
 *       sur l'ObservableList pour éviter {@code ConcurrentModificationException}.</li>
 *   <li>Le handler attend {@code future.get(5s)}.</li>
 *   <li>Si le FX thread n'est pas démarré ({@code TimeoutException} ou
 *       {@code IllegalStateException}) : silencieux, capture ignorée sans impact
 *       sur les tests purement unitaires non-FX.</li>
 *   <li>L'exception originale est <strong>toujours</strong> relancée.</li>
 * </ol>
 *
 * <p>Screenshots générés dans {@code target/test-screenshots/} avec le pattern :
 * {@code ClassName_methodName_timestamp.png}.</p>
 */
public class ScreenshotExtension implements TestExecutionExceptionHandler {

    /** Délai maximum d'attente du FX Application Thread pour la capture (secondes). */
    private static final long FX_TIMEOUT_SECONDS = 5L;

    /** Dossier de sortie des screenshots, relatif au working directory Maven. */
    private static final Path SCREENSHOT_DIR = Paths.get("target", "test-screenshots");

    /**
     * Intercepte toute exception de test, tente une capture d'écran sur le FX thread,
     * puis relance systématiquement l'exception originale.
     *
     * @param ctx       contexte JUnit 5 du test échoué
     * @param throwable exception levée par le test
     * @throws Throwable l'exception originale, toujours relancée sans modification
     */
    @Override
    public void handleTestExecutionException(ExtensionContext ctx, Throwable throwable)
            throws Throwable {

        CompletableFuture<Void> future = new CompletableFuture<>();

        Platform.runLater(() -> {
            try {
                // Copie défensive obligatoire : ne jamais itérer directement sur
                // Window.getWindows() (ObservableList non thread-safe).
                List<Window> windows = new ArrayList<>(Window.getWindows());
                for (Window w : windows) {
                    if (w instanceof Stage s && s.isShowing()) {
                        captureStage(ctx, s);
                    }
                }
                future.complete(null);
            } catch (Exception e) {
                future.completeExceptionally(e);
            }
        });

        try {
            future.get(FX_TIMEOUT_SECONDS, TimeUnit.SECONDS);
        } catch (TimeoutException | IllegalStateException e) {
            // FX thread non démarré (test non-UI ou plateforme sans JavaFX) — silencieux
            System.err.println("⚠ ScreenshotExtension : FX thread non disponible ("
                    + e.getClass().getSimpleName() + "), capture ignorée.");
        } catch (ExecutionException e) {
            // Capture échouée (scène nulle, etc.) — log mais pas de blocage
            System.err.println("⚠ ScreenshotExtension : capture échouée — "
                    + (e.getCause() != null ? e.getCause().getMessage() : e.getMessage()));
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }

        // Toujours relancer l'exception originale — ne jamais masquer un échec de test
        throw throwable;
    }

    /**
     * Capture un screenshot de la scène d'un {@link Stage} visible et l'écrit sur disque.
     *
     * @param ctx   contexte JUnit 5 (utilisé pour nommer le fichier)
     * @param stage fenêtre JavaFX visible dont la scène sera capturée
     * @throws Exception si la création du dossier, la capture ou l'écriture PNG échoue
     */
    private void captureStage(ExtensionContext ctx, Stage stage) throws Exception {
        if (stage.getScene() == null) {
            return;
        }

        String className  = ctx.getTestClass()
                .map(Class::getSimpleName)
                .orElse("UnknownTest");
        String methodName = ctx.getTestMethod()
                .map(java.lang.reflect.Method::getName)
                .orElse("unknownMethod");
        String timestamp  = String.valueOf(System.currentTimeMillis());
        String fileName   = className + "_" + methodName + "_" + timestamp + ".png";

        Files.createDirectories(SCREENSHOT_DIR);
        File outputFile = SCREENSHOT_DIR.resolve(fileName).toFile();

        ImageIO.write(
                SwingFXUtils.fromFXImage(stage.getScene().snapshot(null), null),
                "png",
                outputFile
        );
        System.out.println("📸 Screenshot capturé : " + outputFile.getAbsolutePath());
    }
}

