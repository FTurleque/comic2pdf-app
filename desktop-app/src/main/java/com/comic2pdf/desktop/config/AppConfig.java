package com.comic2pdf.desktop.config;

import java.util.HashMap;
import java.util.Map;

/**
 * Configuration de l'application desktop comic2pdf.
 *
 * <p>Persistée dans {@code %APPDATA%\comic2pdf\config.json} (Windows)
 * ou {@code ${XDG_CONFIG_HOME:-~/.config}/comic2pdf/config.json} (Unix).
 * Envoyée partiellement à l'orchestrateur via {@code POST /config}.</p>
 *
 * <p><b>Note sécurité</b> : le champ {@code apiKey} est persisté localement mais
 * n'est JAMAIS inclus dans le payload envoyé à l'orchestrateur ({@link #toOrchPayload()}).
 * La priorité de résolution est : env var {@code ORCHESTRATOR_API_KEY} &gt; ce champ.</p>
 */
public class AppConfig {

    /** URL de l'orchestrateur. Défaut : {@code http://localhost:8080}. */
    private String orchestratorUrl = "http://localhost:8080";

    /** Concurrence PREP (nombre de jobs de préparation simultanés). Défaut : 2. */
    private int prepConcurrency = 2;

    /** Concurrence OCR (nombre de jobs OCR simultanés). Défaut : 1. */
    private int ocrConcurrency = 1;

    /** Timeout par job en secondes. Défaut : 600. */
    private int jobTimeoutSeconds = 600;

    /** Langue OCR par défaut. Défaut : {@code fra+eng}. */
    private String defaultOcrLang = "fra+eng";

    /**
     * Clé API optionnelle pour l'authentification auprès de l'orchestrateur (header {@code X-Api-Key}).
     *
     * <p><b>Sécurité</b> :</p>
     * <ul>
     *   <li>Ne jamais logger cette valeur.</li>
     *   <li>Non transmise dans {@link #toOrchPayload()}.</li>
     *   <li>Priorité env var {@code ORCHESTRATOR_API_KEY} &gt; ce champ (résolue dans {@code ConfigService}).</li>
     * </ul>
     * <p>Défaut : chaîne vide (authentification désactivée).</p>
     */
    private String apiKey = "";

    /**
     * Construit une configuration avec les valeurs par défaut.
     */
    public AppConfig() {}

    // -----------------------------------------------------------------------
    // Getters / Setters
    // -----------------------------------------------------------------------

    /** @return URL de base de l'orchestrateur. */
    public String getOrchestratorUrl() { return orchestratorUrl; }

    /** @param orchestratorUrl Nouvelle URL de l'orchestrateur. */
    public void setOrchestratorUrl(String orchestratorUrl) {
        this.orchestratorUrl = orchestratorUrl;
    }

    /** @return Concurrence PREP. */
    public int getPrepConcurrency() { return prepConcurrency; }

    /** @param prepConcurrency Nouvelle valeur de concurrence PREP. */
    public void setPrepConcurrency(int prepConcurrency) { this.prepConcurrency = prepConcurrency; }

    /** @return Concurrence OCR. */
    public int getOcrConcurrency() { return ocrConcurrency; }

    /** @param ocrConcurrency Nouvelle valeur de concurrence OCR. */
    public void setOcrConcurrency(int ocrConcurrency) { this.ocrConcurrency = ocrConcurrency; }

    /** @return Timeout job en secondes. */
    public int getJobTimeoutSeconds() { return jobTimeoutSeconds; }

    /** @param jobTimeoutSeconds Nouveau timeout en secondes. */
    public void setJobTimeoutSeconds(int jobTimeoutSeconds) {
        this.jobTimeoutSeconds = jobTimeoutSeconds;
    }

    /** @return Langue OCR par défaut. */
    public String getDefaultOcrLang() { return defaultOcrLang; }

    /** @param defaultOcrLang Nouvelle langue OCR. */
    public void setDefaultOcrLang(String defaultOcrLang) {
        this.defaultOcrLang = defaultOcrLang;
    }

    /**
     * Retourne la clé API locale. Peut être vide si non configurée.
     *
     * <p><b>Attention</b> : ne jamais afficher ni logger cette valeur.</p>
     *
     * @return Clé API, ou chaîne vide si absente.
     */
    public String getApiKey() { return apiKey; }

    /**
     * Définit la clé API locale.
     *
     * @param apiKey Nouvelle clé API. {@code null} est converti en chaîne vide.
     */
    public void setApiKey(String apiKey) {
        this.apiKey = (apiKey != null) ? apiKey : "";
    }

    // -----------------------------------------------------------------------
    // Utilitaires
    // -----------------------------------------------------------------------

    /**
     * Convertit la config en payload JSON compatible avec {@code POST /config} de l'orchestrateur.
     * Les champs utilisent le format snake_case attendu par l'API Python.
     *
     * <p><b>Note</b> : {@code apiKey} est intentionnellement exclu de ce payload.</p>
     *
     * @return Map prête à être sérialisée en JSON.
     */
    public Map<String, Object> toOrchPayload() {
        Map<String, Object> payload = new HashMap<>();
        payload.put("prep_concurrency", prepConcurrency);
        payload.put("ocr_concurrency", ocrConcurrency);
        payload.put("job_timeout_s", jobTimeoutSeconds);
        payload.put("default_ocr_lang", defaultOcrLang);
        return payload;
    }
}

