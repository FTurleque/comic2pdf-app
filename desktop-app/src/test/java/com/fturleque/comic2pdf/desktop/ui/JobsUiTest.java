package com.fturleque.comic2pdf.desktop.ui;

import com.sun.net.httpserver.HttpServer;
import javafx.scene.control.TableView;
import org.junit.jupiter.api.*;
import org.testfx.framework.junit5.ApplicationTest;
import org.testfx.util.WaitForAsyncUtils;
import javafx.stage.Stage;

import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Test UI : vérifie que le refresh manuel des jobs remplit la table
 * depuis un stub HTTP local {@code GET /jobs}.
 *
 * <p>Note TestFX JUnit 5 : {@code start()} est appelé AVANT {@code @BeforeEach}.
 * Le stub HTTP et les overrides sont initialisés dans {@code @BeforeAll} (statique)
 * pour garantir leur présence au démarrage de l'application.</p>
 *
 * <p>autoRefresh=false : aucun poll réseau réel, uniquement le clic sur
 * {@code #jobsRefreshBtn} déclenche la requête vers le stub.</p>
 */
@Tag("ui")
class JobsUiTest extends ApplicationTest {

    private static HttpServer stubServer;

    @BeforeAll
    static void startStub() throws Exception {
        // Stub HTTP sur port éphémère — répond à GET /jobs avec 1 job
        stubServer = HttpServer.create(new InetSocketAddress(0), 0);
        stubServer.createContext("/jobs", exchange -> {
            String json = """
                    [{"jobKey":"k1","state":"DONE","stage":"DONE",
                      "attempt":"1","updatedAt":"2026-01-01","inputName":"comic.cbz"}]
                    """;
            byte[] bytes = json.getBytes(StandardCharsets.UTF_8);
            exchange.getResponseHeaders().add("Content-Type", "application/json");
            exchange.sendResponseHeaders(200, bytes.length);
            try (var os = exchange.getResponseBody()) {
                os.write(bytes);
            }
        });
        stubServer.start();

        int port = stubServer.getAddress().getPort();
        TestableMainApp.orchestratorUrlOverride = "http://localhost:" + port;
        TestableMainApp.jobsAutoRefreshOverride = false;
    }

    @Override
    public void start(Stage stage) throws Exception {
        new TestableMainApp().start(stage);
    }

    @AfterAll
    static void stopStub() {
        stubServer.stop(0);
        TestableMainApp.resetOverrides();
    }

    @Test
    @DisplayName("Refresh manuel : table Jobs contient 1 ligne après réponse stub GET /jobs")
    void forceRefreshAffiche1Job() {
        WaitForAsyncUtils.waitForFxEvents();

        // Naviguer vers l'onglet Jobs
        clickOn("#tabJobs");
        WaitForAsyncUtils.waitForFxEvents();

        // Cliquer le bouton Rafraîchir maintenant
        clickOn("#jobsRefreshBtn");

        // Attendre la réponse HTTP + le Platform.runLater de updateTable (max 3s)
        long deadline = System.currentTimeMillis() + 3_000;
        TableView<?> table;
        do {
            WaitForAsyncUtils.waitForFxEvents();
            WaitForAsyncUtils.sleep(100, java.util.concurrent.TimeUnit.MILLISECONDS);
            table = lookup("#jobsTable").query();
        } while (table.getItems().isEmpty() && System.currentTimeMillis() < deadline);

        assertNotNull(table, "#jobsTable doit exister");
        assertEquals(1, table.getItems().size(),
                "1 job attendu dans la table après refresh manuel");
    }
}

