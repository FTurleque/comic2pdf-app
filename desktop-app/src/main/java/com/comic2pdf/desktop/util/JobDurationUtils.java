package com.comic2pdf.desktop.util;

import java.time.Duration;
import java.time.Instant;
import java.time.format.DateTimeParseException;

/**
 * Utilitaire de calcul de durée pour les jobs.
 *
 * <p>Retourne {@code "N/A"} si {@code startedAt} ou {@code endedAt}
 * sont absents, vides ou malformés — aucune exception propagée.</p>
 */
public final class JobDurationUtils {

    private JobDurationUtils() { }

    /**
     * Calcule la durée entre deux horodatages ISO-8601.
     *
     * @param startedAt Horodatage de début (ISO-8601), ou vide/null.
     * @param endedAt   Horodatage de fin (ISO-8601), ou vide/null.
     * @return Durée au format {@code HH:mm:ss}, ou {@code "N/A"} si impossible.
     */
    public static String compute(String startedAt, String endedAt) {
        if (startedAt == null || startedAt.isBlank()) return "N/A";
        if (endedAt   == null || endedAt.isBlank())   return "N/A";
        try {
            Instant start = Instant.parse(startedAt);
            Instant end   = Instant.parse(endedAt);
            Duration d = Duration.between(start, end);
            if (d.isNegative()) return "N/A";
            long h = d.toHours();
            long m = d.toMinutesPart();
            long s = d.toSecondsPart();
            return String.format("%02d:%02d:%02d", h, m, s);
        } catch (DateTimeParseException e) {
            return "N/A";
        }
    }
}

