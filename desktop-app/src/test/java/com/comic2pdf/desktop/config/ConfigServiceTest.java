package com.comic2pdf.desktop.config;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.io.IOException;
import java.nio.file.Path;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests unitaires de {@link ConfigService} — sérialisation/persistance locale config.json.
 * Isolation filesystem via {@code @TempDir} (JUnit 5).
 */
class ConfigServiceTest {

    @Test
    @DisplayName("load() retourne config par défaut si fichier absent")
    void load_retourneConfigDefaut_siFichierAbsent(@TempDir Path tmpDir) {
        Path cfgPath = tmpDir.resolve("config.json");
        ConfigService svc = new ConfigService(new ObjectMapper(), cfgPath);

        AppConfig cfg = svc.load();

        assertNotNull(cfg);
        assertEquals("http://localhost:8080", cfg.getOrchestratorUrl());
        assertEquals(2, cfg.getPrepConcurrency());
        assertEquals(1, cfg.getOcrConcurrency());
        assertEquals(600, cfg.getJobTimeoutSeconds());
        assertEquals("fra+eng", cfg.getDefaultOcrLang());
    }

    @Test
    @DisplayName("save() puis load() retourne les mêmes valeurs")
    void saveEtLoad_retourneMemeValeurs(@TempDir Path tmpDir) throws IOException {
        Path cfgPath = tmpDir.resolve("config.json");
        ConfigService svc = new ConfigService(new ObjectMapper(), cfgPath);

        AppConfig original = new AppConfig();
        original.setOrchestratorUrl("http://prod-orch:9090");
        original.setPrepConcurrency(4);
        original.setOcrConcurrency(2);
        original.setJobTimeoutSeconds(1200);
        original.setDefaultOcrLang("eng");

        svc.save(original);
        AppConfig loaded = svc.load();

        assertEquals("http://prod-orch:9090", loaded.getOrchestratorUrl());
        assertEquals(4, loaded.getPrepConcurrency());
        assertEquals(2, loaded.getOcrConcurrency());
        assertEquals(1200, loaded.getJobTimeoutSeconds());
        assertEquals("eng", loaded.getDefaultOcrLang());
    }

    @Test
    @DisplayName("save() crée les répertoires intermédiaires manquants")
    void save_creeRepertoiresIntermediaires(@TempDir Path tmpDir) throws IOException {
        Path cfgPath = tmpDir.resolve("niveau1").resolve("niveau2").resolve("config.json");
        ConfigService svc = new ConfigService(new ObjectMapper(), cfgPath);

        svc.save(new AppConfig());

        assertTrue(java.nio.file.Files.exists(cfgPath), "config.json doit exister");
    }

    @Test
    @DisplayName("load() retourne config par défaut si JSON corrompu")
    void load_retourneDefaut_siJsonCorrompu(@TempDir Path tmpDir) throws IOException {
        Path cfgPath = tmpDir.resolve("config.json");
        java.nio.file.Files.writeString(cfgPath, "{ invalide json !!!");
        ConfigService svc = new ConfigService(new ObjectMapper(), cfgPath);

        AppConfig cfg = svc.load();

        assertNotNull(cfg, "Doit retourner un objet non null même si JSON corrompu");
        assertEquals("http://localhost:8080", cfg.getOrchestratorUrl());
    }

    @Test
    @DisplayName("toOrchPayload() contient les clés snake_case attendues")
    void toOrchPayload_contientClesSnakeCase() {
        AppConfig cfg = new AppConfig();
        cfg.setPrepConcurrency(3);
        cfg.setOcrConcurrency(2);
        cfg.setJobTimeoutSeconds(900);
        cfg.setDefaultOcrLang("fra");

        Map<String, Object> payload = cfg.toOrchPayload();

        assertTrue(payload.containsKey("prep_concurrency"));
        assertTrue(payload.containsKey("ocr_concurrency"));
        assertTrue(payload.containsKey("job_timeout_s"));
        assertTrue(payload.containsKey("default_ocr_lang"));
        assertEquals(3, payload.get("prep_concurrency"));
        assertEquals("fra", payload.get("default_ocr_lang"));
    }
}

