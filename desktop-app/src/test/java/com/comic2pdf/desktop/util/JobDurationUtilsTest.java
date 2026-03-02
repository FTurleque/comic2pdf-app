package com.comic2pdf.desktop.util;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests unitaires de {@link JobDurationUtils}.
 *
 * <p>Couvre le risque R1 : {@code startedAt}/{@code endedAt} absents ou malformés
 * retournent {@code "N/A"} sans aucune exception — y compris dans le cas du stub
 * {@code JobsUiTest} qui ne fournit pas ces champs.</p>
 */
@DisplayName("JobDurationUtils")
class JobDurationUtilsTest {

    // -----------------------------------------------------------------------
    // Cas "N/A" — entrées manquantes ou invalides
    // -----------------------------------------------------------------------

    @Test
    @DisplayName("startedAt null => N/A")
    void startedAtNull() {
        assertEquals("N/A", JobDurationUtils.compute(null, "2026-01-01T00:01:00Z"));
    }

    @Test
    @DisplayName("startedAt vide => N/A  (cas stub JobsUiTest : champ absent)")
    void startedAtVide() {
        assertEquals("N/A", JobDurationUtils.compute("", "2026-01-01T00:01:00Z"));
    }

    @Test
    @DisplayName("endedAt null => N/A")
    void endedAtNull() {
        assertEquals("N/A", JobDurationUtils.compute("2026-01-01T00:00:00Z", null));
    }

    @Test
    @DisplayName("endedAt vide => N/A")
    void endedAtVide() {
        assertEquals("N/A", JobDurationUtils.compute("2026-01-01T00:00:00Z", ""));
    }

    @Test
    @DisplayName("les deux vides => N/A  (cas stub JobsUiTest)")
    void tousDeuxVides() {
        assertEquals("N/A", JobDurationUtils.compute("", ""));
    }

    @Test
    @DisplayName("startedAt malformed => N/A sans crash")
    void startedAtMalformed() {
        assertEquals("N/A", JobDurationUtils.compute("pas-une-date", "2026-01-01T00:01:00Z"));
    }

    @Test
    @DisplayName("endedAt malformed => N/A sans crash")
    void endedAtMalformed() {
        assertEquals("N/A", JobDurationUtils.compute("2026-01-01T00:00:00Z", "invalid"));
    }

    @Test
    @DisplayName("duree negative (end < start) => N/A")
    void dureeNegative() {
        assertEquals("N/A", JobDurationUtils.compute(
                "2026-01-01T00:01:00Z", "2026-01-01T00:00:00Z"));
    }

    // -----------------------------------------------------------------------
    // Cas valides
    // -----------------------------------------------------------------------

    @Test
    @DisplayName("duree valide 90s => 00:01:30")
    void dureeValide90s() {
        assertEquals("00:01:30", JobDurationUtils.compute(
                "2026-01-01T00:00:00Z", "2026-01-01T00:01:30Z"));
    }

    @Test
    @DisplayName("duree valide 3h4m5s => 03:04:05")
    void dureeValide3h() {
        assertEquals("03:04:05", JobDurationUtils.compute(
                "2026-01-01T00:00:00Z", "2026-01-01T03:04:05Z"));
    }

    @Test
    @DisplayName("duree nulle (start == end) => 00:00:00")
    void dureeNulle() {
        assertEquals("00:00:00", JobDurationUtils.compute(
                "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"));
    }
}

