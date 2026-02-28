package com.fturleque.comic2pdf.desktop.ui;

import javafx.scene.control.TableView;
import org.junit.jupiter.api.*;
import org.junit.jupiter.api.io.TempDir;
import org.testfx.framework.junit5.ApplicationTest;
import org.testfx.util.WaitForAsyncUtils;
import javafx.stage.Stage;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Test UI : vérifie que le refresh doublons lit un rapport JSON
 * et affiche exactement 1 ligne dans la table.
 *
 * <p>Note TestFX JUnit 5 : {@code start()} est appelé AVANT {@code @BeforeEach}.
 * Les overrides statiques sont donc initialisés dans un {@code @BeforeAll} statique
 * combiné avec {@code @TempDir} statique pour garantir que le dossier existe
 * au moment où {@code TestableMainApp.start()} est invoqué.</p>
 */
@Tag("ui")
class DuplicatesUiTest extends ApplicationTest {

    @TempDir
    static Path dataDir;

    @BeforeAll
    static void prepareOverrides() throws Exception {
        // Préparer le rapport avant le démarrage de l'app (start() est appelé après @BeforeAll)
        Path reportsDir = dataDir.resolve("reports").resolve("duplicates");
        Files.createDirectories(reportsDir);

        String json = """
                {
                  "jobKey": "aabb1122__ccdd3344",
                  "incoming": { "fileName": "MonComic.cbz" },
                  "existing": { "state": "DONE" }
                }
                """;
        Files.writeString(reportsDir.resolve("aabb1122__ccdd3344.json"), json);

        TestableMainApp.dataDirOverride = Optional.of(dataDir);
        TestableMainApp.jobsAutoRefreshOverride = Optional.of(false);
    }

    @Override
    public void start(Stage stage) throws Exception {
        new TestableMainApp().start(stage);
    }

    @AfterAll
    static void tearDownAll() {
        TestableMainApp.resetOverrides();
    }

    @Test
    @DisplayName("Refresh doublons : table contient 1 ligne après lecture du rapport JSON")
    void refreshAffiche1Doublon() {
        WaitForAsyncUtils.waitForFxEvents();

        // Le constructeur MainView appelle refreshDuplicates() avec le dataDir injecté :
        // la table peut déjà être remplie. Si non, cliquer le bouton.
        @SuppressWarnings("unchecked")
        TableView<?> tableAvant = lookup("#duplicatesTable").query();
        assertNotNull(tableAvant, "#duplicatesTable doit exister");

        // Forcer un refresh explicite pour s'assurer que la table est à jour
        clickOn("#duplicatesRefreshBtn");
        WaitForAsyncUtils.waitForFxEvents();

        @SuppressWarnings("unchecked")
        TableView<?> table = lookup("#duplicatesTable").query();
        assertEquals(1, table.getItems().size(),
                "1 doublon attendu dans la table après refresh");
    }
}

