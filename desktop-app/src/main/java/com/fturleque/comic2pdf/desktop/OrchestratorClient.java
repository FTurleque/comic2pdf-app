package com.fturleque.comic2pdf.desktop;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fturleque.comic2pdf.desktop.config.AppConfig;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;

/**
 * Client HTTP vers l'API d'observabilité de l'orchestrateur.
 *
 * <p>Utilise {@code java.net.http.HttpClient} (Java 11+, stdlib — aucune dépendance Maven).</p>
 * <p>URL configurable : {@code ORCHESTRATOR_URL} (env) ou champ UI, défaut {@code http://localhost:8080}.</p>
 */
public class OrchestratorClient {

    private static final String ENV_URL = "ORCHESTRATOR_URL";
    private static final String DEFAULT_URL = "http://localhost:8080";
    private static final Duration TIMEOUT = Duration.ofSeconds(5);

    private final HttpClient httpClient;
    private final ObjectMapper mapper;
    private volatile String baseUrl;

    /**
     * Construit un client en lisant {@code ORCHESTRATOR_URL} depuis l'environnement,
     * ou en utilisant la valeur par défaut {@code http://localhost:8080}.
     */
    public OrchestratorClient() {
        this(
            Optional.ofNullable(System.getenv(ENV_URL)).filter(s -> !s.isBlank()).orElse(DEFAULT_URL)
        );
    }

    /**
     * Construit un client avec une URL de base explicite.
     *
     * @param baseUrl URL de base de l'orchestrateur (ex: {@code http://localhost:8080}).
     */
    public OrchestratorClient(String baseUrl) {
        this.baseUrl = baseUrl.replaceAll("/+$", "");
        this.httpClient = HttpClient.newBuilder()
                .connectTimeout(TIMEOUT)
                .build();
        this.mapper = new ObjectMapper();
    }

    /**
     * Modifie l'URL de base (permet le changement depuis l'UI sans recréer le client).
     *
     * @param url Nouvelle URL de base.
     */
    public void setBaseUrl(String url) {
        this.baseUrl = url.replaceAll("/+$", "");
    }

    /** @return URL de base courante. */
    public String getBaseUrl() { return baseUrl; }

    // -----------------------------------------------------------------------
    // Endpoints
    // -----------------------------------------------------------------------

    /**
     * Récupère la liste de tous les jobs.
     *
     * @return Liste de {@link JobRow}, vide si erreur de communication.
     */
    public List<JobRow> getJobs() {
        try {
            String body = get("/jobs");
            JsonNode arr = mapper.readTree(body);
            List<JobRow> rows = new ArrayList<>();
            for (JsonNode node : arr) {
                rows.add(parseJobRow(node));
            }
            return rows;
        } catch (Exception e) {
            return List.of();
        }
    }

    /**
     * Récupère les détails d'un job spécifique.
     *
     * @param jobKey Clé du job.
     * @return {@link Optional} contenant le {@link JobRow}, ou vide si 404/erreur.
     */
    public Optional<JobRow> getJob(String jobKey) {
        try {
            String body = get("/jobs/" + jobKey);
            JsonNode node = mapper.readTree(body);
            return Optional.of(parseJobRow(node));
        } catch (Exception e) {
            return Optional.empty();
        }
    }

    /**
     * Récupère les métriques courantes de l'orchestrateur.
     *
     * @return Nœud JSON brut des métriques, ou nœud vide si erreur.
     */
    public JsonNode getMetrics() {
        try {
            String body = get("/metrics");
            return mapper.readTree(body);
        } catch (Exception e) {
            return mapper.createObjectNode();
        }
    }

    /**
     * Envoie une nouvelle configuration à l'orchestrateur via {@code POST /config}.
     *
     * @param config Configuration à appliquer.
     * @return {@code true} si l'envoi a réussi (HTTP 200), {@code false} sinon.
     */
    public boolean postConfig(AppConfig config) {
        try {
            String json = mapper.writeValueAsString(config.toOrchPayload());
            String body = post("/config", json);
            return body != null;
        } catch (Exception e) {
            return false;
        }
    }

    // -----------------------------------------------------------------------
    // Helpers HTTP
    // -----------------------------------------------------------------------

    private String get(String path) throws Exception {
        HttpRequest req = HttpRequest.newBuilder()
                .uri(URI.create(baseUrl + path))
                .timeout(TIMEOUT)
                .GET()
                .build();
        HttpResponse<String> resp = httpClient.send(req, HttpResponse.BodyHandlers.ofString());
        if (resp.statusCode() == 404) {
            throw new RuntimeException("404 Not Found: " + path);
        }
        if (resp.statusCode() < 200 || resp.statusCode() >= 300) {
            throw new RuntimeException("HTTP " + resp.statusCode() + " pour " + path);
        }
        return resp.body();
    }

    private String post(String path, String jsonBody) throws Exception {
        HttpRequest req = HttpRequest.newBuilder()
                .uri(URI.create(baseUrl + path))
                .timeout(TIMEOUT)
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(jsonBody))
                .build();
        HttpResponse<String> resp = httpClient.send(req, HttpResponse.BodyHandlers.ofString());
        if (resp.statusCode() < 200 || resp.statusCode() >= 300) {
            throw new RuntimeException("HTTP " + resp.statusCode() + " pour POST " + path);
        }
        return resp.body();
    }

    private JobRow parseJobRow(JsonNode node) {
        return new JobRow(
                node.path("jobKey").asText(""),
                node.path("state").asText(""),
                node.path("stage").asText(""),
                String.valueOf(node.path("attempt").asInt(0)),
                node.path("updatedAt").asText(""),
                node.path("inputName").asText("")
        );
    }
}

