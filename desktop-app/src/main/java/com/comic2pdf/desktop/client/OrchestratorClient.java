package com.comic2pdf.desktop.client;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.comic2pdf.desktop.config.AppConfig;
import com.comic2pdf.desktop.model.JobRow;

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
 * <p>URL configurable via {@code ORCHESTRATOR_URL} (env) ou constructeur explicite.</p>
 *
 * <h2>Authentification</h2>
 * <p>Si une clé API est configurée (via {@link #setApiKey(String)}), elle est transmise
 * dans le header {@code X-Api-Key} sur <b>tous</b> les appels (GET et POST).
 * La clé n'est jamais loguée.</p>
 */
public class OrchestratorClient {

    private static final String ENV_URL = "ORCHESTRATOR_URL";
    private static final String DEFAULT_URL = "http://localhost:8080";
    private static final Duration TIMEOUT = Duration.ofSeconds(5);

    /** Nom du header d'authentification attendu par l'orchestrateur. */
    private static final String HEADER_API_KEY = "X-Api-Key";

    private final HttpClient httpClient;
    private final ObjectMapper mapper;
    private volatile String baseUrl;

    /**
     * Clé API courante (peut être vide).
     * Volatile pour la visibilité thread-safe en lecture (pas de synchronisation lourde requise).
     * Ne jamais logger cette valeur.
     */
    private volatile String apiKey = "";

    /**
     * Construit un client en lisant {@code ORCHESTRATOR_URL} depuis l'environnement,
     * ou en utilisant la valeur par défaut {@code http://localhost:8080}.
     */
    public OrchestratorClient() {
        this(Optional.ofNullable(System.getenv(ENV_URL))
                .filter(s -> !s.isBlank())
                .orElse(DEFAULT_URL));
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
     * Modifie l'URL de base (sans recréer le client).
     *
     * @param url Nouvelle URL de base.
     */
    public void setBaseUrl(String url) {
        this.baseUrl = url.replaceAll("/+$", "");
    }

    /** @return URL de base courante. */
    public String getBaseUrl() { return baseUrl; }

    /**
     * Définit la clé API à utiliser pour l'authentification.
     * Une chaîne vide ou {@code null} désactive l'envoi du header.
     *
     * <p><b>Sécurité</b> : ne jamais logger la valeur de ce paramètre.</p>
     *
     * @param apiKey Clé API ou chaîne vide pour désactiver l'authentification.
     */
    public void setApiKey(String apiKey) {
        this.apiKey = (apiKey != null) ? apiKey : "";
    }

    /**
     * Indique si une clé API est actuellement configurée.
     *
     * @return {@code true} si la clé est non vide.
     */
    public boolean hasApiKey() {
        return !apiKey.isBlank();
    }

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
            return getJobsOrThrow();
        } catch (Exception e) {
            return List.of();
        }
    }

    /**
     * Récupère la liste des jobs en propageant toute exception réseau.
     * Utilisé par {@link com.comic2pdf.desktop.service.ConnectivityService} pour le ping
     * et par {@code JobsController} pour la détection offline.
     *
     * @return Liste de {@link JobRow}.
     * @throws Exception En cas d'erreur réseau ou HTTP.
     */
    public List<JobRow> getJobsOrThrow() throws Exception {
        String body = get("/jobs");
        JsonNode arr = mapper.readTree(body);
        List<JobRow> rows = new ArrayList<>();
        for (JsonNode node : arr) {
            rows.add(parseJobRow(node));
        }
        return rows;
    }

    /**
     * Récupère les détails d'un job spécifique.
     *
     * @param jobKey Clé du job.
     * @return {@link Optional} contenant le {@link JobRow}, ou vide si 404/erreur.
     */
    public Optional<JobRow> getJob(String jobKey) {
        try {
            return Optional.of(getJobOrThrow(jobKey));
        } catch (Exception e) {
            return Optional.empty();
        }
    }

    /**
     * Récupère les détails d'un job en propageant toute exception réseau.
     *
     * @param jobKey Clé du job.
     * @return {@link JobRow} détaillé.
     * @throws Exception En cas d'erreur réseau, HTTP ou job introuvable.
     */
    public JobRow getJobOrThrow(String jobKey) throws Exception {
        String body = get("/jobs/" + jobKey);
        JsonNode node = mapper.readTree(body);
        return parseJobRow(node);
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
     * Le header {@code X-Api-Key} est inclus automatiquement si une clé est configurée.
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
    // Helpers HTTP privés
    // -----------------------------------------------------------------------

    private String get(String path) throws Exception {
        HttpRequest.Builder builder = HttpRequest.newBuilder()
                .uri(URI.create(baseUrl + path))
                .timeout(TIMEOUT)
                .GET();
        injectApiKeyHeader(builder);
        HttpResponse<String> resp = httpClient.send(builder.build(),
                HttpResponse.BodyHandlers.ofString());
        if (resp.statusCode() == 404) {
            throw new RuntimeException("404 Not Found: " + path);
        }
        if (resp.statusCode() < 200 || resp.statusCode() >= 300) {
            throw new RuntimeException("HTTP " + resp.statusCode() + " pour " + path);
        }
        return resp.body();
    }

    private String post(String path, String jsonBody) throws Exception {
        HttpRequest.Builder builder = HttpRequest.newBuilder()
                .uri(URI.create(baseUrl + path))
                .timeout(TIMEOUT)
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(jsonBody));
        injectApiKeyHeader(builder);
        HttpResponse<String> resp = httpClient.send(builder.build(),
                HttpResponse.BodyHandlers.ofString());
        if (resp.statusCode() < 200 || resp.statusCode() >= 300) {
            throw new RuntimeException("HTTP " + resp.statusCode() + " pour POST " + path);
        }
        return resp.body();
    }

    /**
     * Injecte le header {@code X-Api-Key} si une clé est configurée.
     * Ne logue jamais la valeur de la clé.
     *
     * @param builder Constructeur de requête HTTP en cours.
     */
    private void injectApiKeyHeader(HttpRequest.Builder builder) {
        if (!apiKey.isBlank()) {
            builder.header(HEADER_API_KEY, apiKey);
        }
    }

    private JobRow parseJobRow(JsonNode node) {
        return new JobRow(
                node.path("jobKey").asText(""),
                node.path("state").asText(""),
                node.path("stage").asText(""),
                String.valueOf(node.path("attempt").asInt(0)),
                node.path("updatedAt").asText(""),
                node.path("inputName").asText(""),
                node.path("outPdf").asText(""),
                node.path("errorMessage").asText(""),
                node.path("startedAt").asText(""),
                node.path("endedAt").asText("")
        );
    }
}

