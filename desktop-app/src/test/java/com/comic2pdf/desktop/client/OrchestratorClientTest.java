package com.comic2pdf.desktop.client;

import com.comic2pdf.desktop.config.AppConfig;
import com.comic2pdf.desktop.model.JobRow;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.util.concurrent.atomic.AtomicReference;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests unitaires de {@link OrchestratorClient} — sans réseau réel (serveur HTTP embarqué JDK).
 * Vérifie le parsing JSON, la gestion d'URL, les headers d'authentification et la resilience.
 */
class OrchestratorClientTest {

    private HttpServer mockServer;
    private int mockPort;

    @BeforeEach
    void startMockServer() throws IOException {
        mockServer = HttpServer.create(new InetSocketAddress(0), 0);
        mockPort = mockServer.getAddress().getPort();
    }

    @AfterEach
    void stopMockServer() {
        if (mockServer != null) {
            mockServer.stop(0);
        }
    }

    // -----------------------------------------------------------------------
    // Tests constructeur / URL
    // -----------------------------------------------------------------------

    @Test
    @DisplayName("Constructeur utilise l'URL fournie et supprime les slashes de fin")
    void constructeur_utiliseUrlFournie() {
        OrchestratorClient client = new OrchestratorClient("http://test-orch:9090///");
        assertEquals("http://test-orch:9090", client.getBaseUrl());
    }

    @Test
    @DisplayName("setBaseUrl supprime les slashes de fin")
    void setBaseUrl_supprimesSlashFin() {
        OrchestratorClient client = new OrchestratorClient("http://localhost:8080///");
        assertEquals("http://localhost:8080", client.getBaseUrl());
    }

    // -----------------------------------------------------------------------
    // Tests résilience (orchestrateur inaccessible)
    // -----------------------------------------------------------------------

    @Test
    @DisplayName("getJobs() retourne une liste vide si l'orchestrateur est inaccessible")
    void getJobs_retourneListeVide_siOrchInaccessible() {
        OrchestratorClient client = new OrchestratorClient("http://127.0.0.1:19999");
        var jobs = client.getJobs();
        assertNotNull(jobs);
        assertTrue(jobs.isEmpty(), "Doit retourner liste vide si connexion impossible");
    }

    @Test
    @DisplayName("getJob() retourne Optional vide si l'orchestrateur est inaccessible")
    void getJob_retourneOptionalVide_siOrchInaccessible() {
        OrchestratorClient client = new OrchestratorClient("http://127.0.0.1:19999");
        var opt = client.getJob("some-key");
        assertFalse(opt.isPresent(), "Doit retourner Optional vide si connexion impossible");
    }

    @Test
    @DisplayName("getMetrics() retourne un nœud vide si l'orchestrateur est inaccessible")
    void getMetrics_retourneNoeudVide_siOrchInaccessible() {
        OrchestratorClient client = new OrchestratorClient("http://127.0.0.1:19999");
        var metrics = client.getMetrics();
        assertNotNull(metrics);
        assertTrue(metrics.isEmpty(), "Doit retourner noeud vide si connexion impossible");
    }

    @Test
    @DisplayName("postConfig() retourne false si l'orchestrateur est inaccessible")
    void postConfig_retourneFalse_siOrchInaccessible() {
        OrchestratorClient client = new OrchestratorClient("http://127.0.0.1:19999");
        var cfg = new AppConfig();
        boolean result = client.postConfig(cfg);
        assertFalse(result, "Doit retourner false si connexion impossible");
    }

    // -----------------------------------------------------------------------
    // Tests injection du header X-Api-Key
    // -----------------------------------------------------------------------

    @Test
    @DisplayName("setApiKey + hasApiKey : clé non vide est détectée")
    void setApiKey_hasApiKey_retourneTrue() {
        OrchestratorClient client = new OrchestratorClient("http://localhost:8080");
        client.setApiKey("my-secret");
        assertTrue(client.hasApiKey());
    }

    @Test
    @DisplayName("hasApiKey retourne false si clé vide ou null")
    void hasApiKey_retourneFalse_siVideOuNull() {
        OrchestratorClient client = new OrchestratorClient("http://localhost:8080");
        assertFalse(client.hasApiKey(), "Pas de clé par défaut");

        client.setApiKey("");
        assertFalse(client.hasApiKey());

        client.setApiKey(null);
        assertFalse(client.hasApiKey());
    }

    @Test
    @DisplayName("GET /jobs envoie le header X-Api-Key si clé configurée")
    void getJobs_envoyeHeader_siCleConfiguree() throws Exception {
        AtomicReference<String> capturedApiKey = new AtomicReference<>("");

        mockServer.createContext("/jobs", exchange -> {
            capturedApiKey.set(exchange.getRequestHeaders().getFirst("X-Api-Key"));
            String resp = "[]";
            exchange.sendResponseHeaders(200, resp.length());
            try (OutputStream os = exchange.getResponseBody()) {
                os.write(resp.getBytes());
            }
        });
        mockServer.start();

        OrchestratorClient client = new OrchestratorClient("http://127.0.0.1:" + mockPort);
        client.setApiKey("test-secret-key");

        client.getJobs();

        assertEquals("test-secret-key", capturedApiKey.get(),
                "Le header X-Api-Key doit être envoyé avec la clé configurée");
    }

    @Test
    @DisplayName("GET /jobs n'envoie PAS X-Api-Key si clé non configurée")
    void getJobs_nEnvoiePasHeader_siPasDeCle() throws Exception {
        AtomicReference<String> capturedApiKey = new AtomicReference<>("NOT_SET");

        mockServer.createContext("/jobs", exchange -> {
            String header = exchange.getRequestHeaders().getFirst("X-Api-Key");
            capturedApiKey.set(header != null ? header : "ABSENT");
            String resp = "[]";
            exchange.sendResponseHeaders(200, resp.length());
            try (OutputStream os = exchange.getResponseBody()) {
                os.write(resp.getBytes());
            }
        });
        mockServer.start();

        OrchestratorClient client = new OrchestratorClient("http://127.0.0.1:" + mockPort);
        // Pas de setApiKey

        client.getJobs();

        assertEquals("ABSENT", capturedApiKey.get(),
                "Le header X-Api-Key ne doit pas être envoyé si aucune clé n'est configurée");
    }

    @Test
    @DisplayName("POST /config envoie le header X-Api-Key si clé configurée")
    void postConfig_envoyeHeader_siCleConfiguree() throws Exception {
        AtomicReference<String> capturedApiKey = new AtomicReference<>("");

        mockServer.createContext("/config", exchange -> {
            if ("POST".equals(exchange.getRequestMethod())) {
                capturedApiKey.set(exchange.getRequestHeaders().getFirst("X-Api-Key"));
                exchange.getRequestBody().readAllBytes(); // consumer le body
                String resp = "{\"applied\":{}}";
                exchange.sendResponseHeaders(200, resp.length());
                try (OutputStream os = exchange.getResponseBody()) {
                    os.write(resp.getBytes());
                }
            } else {
                exchange.sendResponseHeaders(405, 0);
                exchange.getResponseBody().close();
            }
        });
        mockServer.start();

        OrchestratorClient client = new OrchestratorClient("http://127.0.0.1:" + mockPort);
        client.setApiKey("config-secret");

        boolean result = client.postConfig(new AppConfig());

        assertTrue(result, "postConfig doit retourner true si HTTP 200");
        assertEquals("config-secret", capturedApiKey.get(),
                "Le header X-Api-Key doit être envoyé lors du POST /config");
    }

    @Test
    @DisplayName("postConfig() retourne false si le serveur répond 401")
    void postConfig_retourneFalse_si401() throws Exception {
        mockServer.createContext("/config", exchange -> {
            exchange.getRequestBody().readAllBytes();
            String resp = "{\"error\":\"Unauthorized\"}";
            exchange.sendResponseHeaders(401, resp.length());
            try (OutputStream os = exchange.getResponseBody()) {
                os.write(resp.getBytes());
            }
        });
        mockServer.start();

        OrchestratorClient client = new OrchestratorClient("http://127.0.0.1:" + mockPort);

        boolean result = client.postConfig(new AppConfig());

        assertFalse(result, "postConfig doit retourner false si HTTP 401");
    }

    @Test
    @DisplayName("postConfig() retourne false si le serveur répond 403")
    void postConfig_retourneFalse_si403() throws Exception {
        mockServer.createContext("/config", exchange -> {
            exchange.getRequestBody().readAllBytes();
            String resp = "{\"error\":\"Forbidden\"}";
            exchange.sendResponseHeaders(403, resp.length());
            try (OutputStream os = exchange.getResponseBody()) {
                os.write(resp.getBytes());
            }
        });
        mockServer.start();

        OrchestratorClient client = new OrchestratorClient("http://127.0.0.1:" + mockPort);

        boolean result = client.postConfig(new AppConfig());

        assertFalse(result, "postConfig doit retourner false si HTTP 403");
    }

    // -----------------------------------------------------------------------
    // Tests JobRow
    // -----------------------------------------------------------------------

    @Test
    @DisplayName("JobRow.updateFrom() met à jour correctement tous les champs")
    void jobRow_updateFrom_metAJourTousChamps() {
        JobRow row = new JobRow("key1", "RUNNING", "PREP_RUNNING", "1", "2026-01-01",
                "comic.cbz", "", "");
        JobRow fresh = new JobRow("key1", "DONE", "DONE", "2", "2026-01-02",
                "comic.cbz", "/data/out/comic__job-key1.pdf", "");
        row.updateFrom(fresh);

        assertEquals("DONE", row.getState());
        assertEquals("DONE", row.getStage());
        assertEquals("2", row.getAttempt());
        assertEquals("2026-01-02", row.getUpdatedAt());
        assertEquals("/data/out/comic__job-key1.pdf", row.getOutPdf());
        assertEquals("", row.getErrorMessage());
    }

    @Test
    @DisplayName("JobRow constructeur 6 paramètres : outPdf et errorMessage sont vides")
    void jobRow_constructeur6Params_champsEnrichisVides() {
        JobRow row = new JobRow("k", "DONE", "DONE", "1", "2026-01-01", "f.cbz");
        assertEquals("", row.getOutPdf());
        assertEquals("", row.getErrorMessage());
    }

    @Test
    @DisplayName("getJobs() parse correctement un JSON avec outPdf et errorMessage")
    void getJobs_parseJsonEnrichi() throws Exception {
        String json = "[{\"jobKey\":\"abc__def\",\"state\":\"DONE\",\"stage\":\"DONE\"," +
                "\"attempt\":1,\"updatedAt\":\"2026-01-01T00:00:00Z\"," +
                "\"inputName\":\"comic.cbz\"," +
                "\"outPdf\":\"/data/out/comic__job-abc__def.pdf\"," +
                "\"errorMessage\":\"\"}]";

        mockServer.createContext("/jobs", exchange -> {
            exchange.sendResponseHeaders(200, json.length());
            try (OutputStream os = exchange.getResponseBody()) {
                os.write(json.getBytes());
            }
        });
        mockServer.start();

        OrchestratorClient client = new OrchestratorClient("http://127.0.0.1:" + mockPort);
        var jobs = client.getJobs();

        assertEquals(1, jobs.size());
        assertEquals("abc__def", jobs.get(0).getJobKey());
        assertEquals("/data/out/comic__job-abc__def.pdf", jobs.get(0).getOutPdf());
        assertEquals("", jobs.get(0).getErrorMessage());
    }
}
