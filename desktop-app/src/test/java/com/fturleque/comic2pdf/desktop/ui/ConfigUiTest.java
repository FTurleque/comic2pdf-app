package com.fturleque.comic2pdf.desktop.ui;

import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.*;
import org.testfx.framework.junit5.ApplicationTest;
import org.testfx.util.WaitForAsyncUtils;
import javafx.stage.Stage;

import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.Optional;
import java.util.concurrent.atomic.AtomicReference;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Test UI : vérifie que le bouton "Appliquer" envoie un JSON valide au stub {@code POST /config}.
 *
 * <p>Note TestFX JUnit 5 : {@code start()} est appelé AVANT {@code @BeforeEach}.
 * Le stub HTTP et les overrides sont initialisés dans {@code @BeforeAll} (statique).</p>
 */
@Tag("ui")
class ConfigUiTest extends ApplicationTest {

    private static HttpServer stubServer;
    private static final AtomicReference<String> capturedBody = new AtomicReference<>();

    @BeforeAll
    static void startStub() throws Exception {
        capturedBody.set(null);

        // Stub HTTP sur port éphémère
        stubServer = HttpServer.create(new InetSocketAddress(0), 0);
        stubServer.createContext("/config", exchange -> {
            if ("POST".equalsIgnoreCase(exchange.getRequestMethod())) {
                byte[] bodyBytes = exchange.getRequestBody().readAllBytes();
                capturedBody.set(new String(bodyBytes, StandardCharsets.UTF_8));
                exchange.sendResponseHeaders(200, 0);
                exchange.getResponseBody().close();
            } else {
                // GET /config — répondre {} pour ne pas bloquer le chargement initial
                byte[] resp = "{}".getBytes(StandardCharsets.UTF_8);
                exchange.getResponseHeaders().add("Content-Type", "application/json");
                exchange.sendResponseHeaders(200, resp.length);
                try (var os = exchange.getResponseBody()) {
                    os.write(resp);
                }
            }
        });
        stubServer.start();

        int port = stubServer.getAddress().getPort();
        TestableMainApp.orchestratorUrlOverride = Optional.of("http://localhost:" + port);
        TestableMainApp.jobsAutoRefreshOverride = Optional.of(false);
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
    @DisplayName("Apply Config : le stub POST /config reçoit le JSON avec les clés attendues")
    void applyConfigEnvoieJsonAuStub() throws Exception {
        WaitForAsyncUtils.waitForFxEvents();

        // Naviguer vers l'onglet Configuration
        clickOn("#tabConfig");
        WaitForAsyncUtils.waitForFxEvents();

        // Cliquer "Appliquer"
        clickOn("#applyConfigBtn");
        WaitForAsyncUtils.waitForFxEvents();

        // Attendre que le stub ait reçu la requête POST (max 5s)
        long deadline = System.currentTimeMillis() + 5_000;
        while (capturedBody.get() == null && System.currentTimeMillis() < deadline) {
            Thread.sleep(50);
        }

        String body = capturedBody.get();
        assertNotNull(body, "Le stub doit avoir reçu un body JSON via POST /config");
        assertTrue(body.contains("prep_concurrency"),
                "JSON doit contenir la clé prep_concurrency");
        assertTrue(body.contains("ocr_concurrency"),
                "JSON doit contenir la clé ocr_concurrency");
        assertTrue(body.contains("job_timeout_s"),
                "JSON doit contenir la clé job_timeout_s");
        assertTrue(body.contains("default_ocr_lang"),
                "JSON doit contenir la clé default_ocr_lang");
    }
}

