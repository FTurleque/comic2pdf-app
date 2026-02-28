package com.comic2pdf.desktop;

import com.fasterxml.jackson.databind.JsonNode;
import com.comic2pdf.desktop.config.AppConfig;
import com.comic2pdf.desktop.model.JobRow;

import java.util.List;
import java.util.Optional;

/**
 * Compat stub — délègue vers {@link com.comic2pdf.desktop.client.OrchestratorClient}.
 * Maintenu pour que {@code OrchestratorClientTest} (package {@code com.comic2pdf.desktop})
 * continue de compiler sans modification.
 * À supprimer après migration complète des imports.
 *
 * @deprecated Utiliser {@link com.comic2pdf.desktop.client.OrchestratorClient}.
 */
@Deprecated(since = "2026-03", forRemoval = true)
public class OrchestratorClient {

    private final com.comic2pdf.desktop.client.OrchestratorClient delegate;

    /**
     * Construit un stub en lisant {@code ORCHESTRATOR_URL} depuis l'environnement.
     */
    public OrchestratorClient() {
        this.delegate = new com.comic2pdf.desktop.client.OrchestratorClient();
    }

    /**
     * Construit un stub avec une URL explicite.
     *
     * @param baseUrl URL de base de l'orchestrateur.
     */
    public OrchestratorClient(String baseUrl) {
        this.delegate = new com.comic2pdf.desktop.client.OrchestratorClient(baseUrl);
    }

    /**
     * @param url Nouvelle URL de base.
     */
    public void setBaseUrl(String url) { delegate.setBaseUrl(url); }

    /** @return URL de base courante. */
    public String getBaseUrl() { return delegate.getBaseUrl(); }

    /**
     * @return Liste de {@link JobRow}, vide si erreur.
     */
    public List<JobRow> getJobs() { return delegate.getJobs(); }

    /**
     * @param jobKey Clé du job.
     * @return Optional JobRow.
     */
    public Optional<JobRow> getJob(String jobKey) { return delegate.getJob(jobKey); }

    /**
     * @return Nœud JSON des métriques.
     */
    public JsonNode getMetrics() { return delegate.getMetrics(); }

    /**
     * @param config Configuration à appliquer.
     * @return {@code true} si succès.
     */
    public boolean postConfig(AppConfig config) { return delegate.postConfig(config); }
}
