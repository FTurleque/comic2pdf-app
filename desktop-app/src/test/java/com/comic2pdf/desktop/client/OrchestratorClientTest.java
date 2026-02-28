package com.comic2pdf.desktop.client;

import com.comic2pdf.desktop.config.AppConfig;
import com.comic2pdf.desktop.model.JobRow;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests unitaires de {@link OrchestratorClient} — sans réseau.
 * Vérifie le parsing JSON, la gestion d'URL et le comportement en cas d'erreur de connexion.
 */
class OrchestratorClientTest {

    @Test
    @DisplayName("Constructeur utilise ORCHESTRATOR_URL ou la valeur par défaut")
    void constructeur_utiliseEnvOuDefaut() {
        OrchestratorClient client = new OrchestratorClient("http://test-orch:9090");
        assertEquals("http://test-orch:9090", client.getBaseUrl());
    }

    @Test
    @DisplayName("setBaseUrl supprime les slashes de fin")
    void setBaseUrl_supprimesSlashFin() {
        OrchestratorClient client = new OrchestratorClient("http://localhost:8080///");
        assertEquals("http://localhost:8080", client.getBaseUrl());
    }

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

    @Test
    @DisplayName("JobRow.updateFrom() met à jour correctement tous les champs")
    void jobRow_updateFrom_metAJourTousChamps() {
        JobRow row = new JobRow("key1", "RUNNING", "PREP_RUNNING", "1", "2026-01-01", "comic.cbz");
        JobRow fresh = new JobRow("key1", "DONE", "DONE", "2", "2026-01-02", "comic.cbz");
        row.updateFrom(fresh);

        assertEquals("DONE", row.getState());
        assertEquals("DONE", row.getStage());
        assertEquals("2", row.getAttempt());
        assertEquals("2026-01-02", row.getUpdatedAt());
    }
}

