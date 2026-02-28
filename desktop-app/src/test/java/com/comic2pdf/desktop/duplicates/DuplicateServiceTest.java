package com.comic2pdf.desktop.duplicates;

import com.comic2pdf.desktop.DupRow;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests unitaires de {@link DuplicateService}.
 * Utilise uniquement le filesystem (aucune dépendance JavaFX).
 */
@DisplayName("DuplicateService")
class DuplicateServiceTest {

    private final DuplicateService service = new DuplicateService();

    // -------------------------------------------------------------------------
    // listDuplicates
    // -------------------------------------------------------------------------

    @Test
    @DisplayName("listDuplicates : parse un rapport JSON minimal -> 1 DupRow correct")
    void listDuplicates_parsesReportCorrectly(@TempDir Path dataDir) throws IOException {
        // Préparer le rapport JSON minimal
        Path reportsDir = dataDir.resolve("reports").resolve("duplicates");
        Files.createDirectories(reportsDir);

        String jobKey = "aabb__ccdd";
        String json = """
                {
                  "jobKey": "%s",
                  "incoming": { "fileName": "mon_comic.cbz" },
                  "existing": { "state": "DONE" }
                }
                """.formatted(jobKey);
        Files.writeString(reportsDir.resolve(jobKey + ".json"), json);

        List<DupRow> rows = service.listDuplicates(dataDir);

        assertEquals(1, rows.size(), "Doit retourner 1 doublon");
        DupRow row = rows.get(0);
        assertEquals(jobKey, row.getJobKey());
        assertEquals("mon_comic.cbz", row.getIncomingFile());
        assertEquals("DONE", row.getExistingState());
    }

    @Test
    @DisplayName("listDuplicates : dossier vide -> liste vide")
    void listDuplicates_emptyDir_returnsEmptyList(@TempDir Path dataDir) throws IOException {
        List<DupRow> rows = service.listDuplicates(dataDir);
        assertNotNull(rows);
        assertTrue(rows.isEmpty(), "Un dossier vide doit retourner une liste vide");
    }

    @Test
    @DisplayName("listDuplicates : rapport corrompu -> ignoré, pas de crash")
    void listDuplicates_corruptedReport_ignored(@TempDir Path dataDir) throws IOException {
        Path reportsDir = dataDir.resolve("reports").resolve("duplicates");
        Files.createDirectories(reportsDir);
        Files.writeString(reportsDir.resolve("bad.json"), "{ invalid json !!!}");

        // Un rapport valide en parallèle
        Files.writeString(reportsDir.resolve("good__key.json"),
                """
                {"jobKey":"good__key","incoming":{"fileName":"f.cbz"},"existing":{"state":"DONE"}}
                """);

        List<DupRow> rows = service.listDuplicates(dataDir);
        // Le rapport corrompu est ignoré, le bon est lu
        assertEquals(1, rows.size());
        assertEquals("good__key", rows.get(0).getJobKey());
    }

    @Test
    @DisplayName("listDuplicates : crée le dossier reports/duplicates s'il est absent")
    void listDuplicates_createsMissingDir(@TempDir Path dataDir) throws IOException {
        // Ne pas créer le dossier à l'avance
        assertDoesNotThrow(() -> service.listDuplicates(dataDir));
        assertTrue(Files.exists(dataDir.resolve("reports").resolve("duplicates")));
    }

    // -------------------------------------------------------------------------
    // writeDecision
    // -------------------------------------------------------------------------

    @Test
    @DisplayName("writeDecision : écrit decision.json au bon chemin")
    void writeDecision_writesAtCorrectPath(@TempDir Path dataDir) throws IOException {
        String jobKey = "deadbeef__cafe";
        Path result = service.writeDecision(dataDir, jobKey, DuplicateDecision.DISCARD);

        Path expected = dataDir.resolve("hold").resolve("duplicates").resolve(jobKey).resolve("decision.json");
        assertEquals(expected.toAbsolutePath(), result.toAbsolutePath());
        assertTrue(Files.exists(result), "decision.json doit exister");
    }

    @Test
    @DisplayName("writeDecision DISCARD : action correcte dans le JSON")
    void writeDecision_discard_actionCorrect(@TempDir Path dataDir) throws IOException {
        String jobKey = "test__discard";
        service.writeDecision(dataDir, jobKey, DuplicateDecision.DISCARD);

        Path decisionPath = dataDir.resolve("hold").resolve("duplicates").resolve(jobKey).resolve("decision.json");
        String content = Files.readString(decisionPath);
        assertTrue(content.contains("DISCARD"), "L'action DISCARD doit être dans le JSON");
        assertFalse(content.contains("nonce"), "Pas de nonce pour DISCARD");
    }

    @Test
    @DisplayName("writeDecision FORCE_REPROCESS : nonce présent dans le JSON")
    void writeDecision_forceReprocess_hasNonce(@TempDir Path dataDir) throws IOException {
        String jobKey = "test__force";
        service.writeDecision(dataDir, jobKey, DuplicateDecision.FORCE_REPROCESS);

        Path decisionPath = dataDir.resolve("hold").resolve("duplicates").resolve(jobKey).resolve("decision.json");
        String content = Files.readString(decisionPath);
        assertTrue(content.contains("FORCE_REPROCESS"));
        assertTrue(content.contains("nonce"), "Un nonce doit être inclus pour FORCE_REPROCESS");
    }

    @Test
    @DisplayName("writeDecision : crée les dossiers intermédiaires manquants")
    void writeDecision_createsMissingDirectories(@TempDir Path dataDir) throws IOException {
        String jobKey = "nouveau__job";
        // hold/duplicates/<jobKey>/ n'existe pas encore
        Path holdDir = dataDir.resolve("hold").resolve("duplicates").resolve(jobKey);
        assertFalse(Files.exists(holdDir), "Le dossier ne doit pas encore exister");

        service.writeDecision(dataDir, jobKey, DuplicateDecision.USE_EXISTING_RESULT);

        assertTrue(Files.exists(holdDir), "Le dossier doit avoir été créé");
        assertTrue(Files.exists(holdDir.resolve("decision.json")), "decision.json doit exister");
    }

    @Test
    @DisplayName("writeDecision USE_EXISTING_RESULT : pas de nonce")
    void writeDecision_useExisting_noNonce(@TempDir Path dataDir) throws IOException {
        service.writeDecision(dataDir, "jk__ue", DuplicateDecision.USE_EXISTING_RESULT);
        Path p = dataDir.resolve("hold").resolve("duplicates").resolve("jk__ue").resolve("decision.json");
        String content = Files.readString(p);
        assertTrue(content.contains("USE_EXISTING_RESULT"));
        assertFalse(content.contains("nonce"));
    }
}

