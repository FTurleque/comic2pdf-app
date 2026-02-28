package com.comic2pdf.desktop.duplicates;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.comic2pdf.desktop.DupRow;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.stream.Collectors;
import java.util.stream.Stream;

/**
 * Service pur de gestion des doublons côté desktop.
 * Encapsule la lecture des rapports JSON et l'écriture des décisions
 * sans dépendance directe à l'interface graphique (testable unitairement).
 *
 * <p>Responsabilités :</p>
 * <ul>
 *   <li>Lire {@code data/reports/duplicates/*.json} et les exposer en liste de {@link DupRow}.</li>
 *   <li>Écrire {@code data/hold/duplicates/<jobKey>/decision.json} avec l'action choisie.</li>
 * </ul>
 */
public class DuplicateService {

    private final ObjectMapper mapper;

    /**
     * Construit un {@code DuplicateService} avec un {@link ObjectMapper} Jackson par défaut.
     */
    public DuplicateService() {
        this.mapper = new ObjectMapper();
    }

    /**
     * Construit un {@code DuplicateService} avec un {@link ObjectMapper} fourni.
     * Utile pour les tests.
     *
     * @param mapper ObjectMapper à utiliser.
     */
    public DuplicateService(ObjectMapper mapper) {
        this.mapper = mapper;
    }

    /**
     * Liste tous les doublons en attente de décision.
     * Lit les fichiers {@code *.json} présents dans {@code <dataDir>/reports/duplicates/}.
     *
     * @param dataDir Racine du répertoire {@code data/}.
     * @return Liste de {@link DupRow} (peut être vide, jamais null).
     * @throws IOException En cas d'erreur de lecture du dossier.
     */
    public List<DupRow> listDuplicates(Path dataDir) throws IOException {
        Path reports = dataDir.resolve("reports").resolve("duplicates");
        Files.createDirectories(reports);

        List<DupRow> rows = new ArrayList<>();
        try (Stream<Path> stream = Files.list(reports)) {
            List<Path> jsonFiles = stream
                    .filter(p -> p.toString().endsWith(".json"))
                    .collect(Collectors.toList());

            for (Path p : jsonFiles) {
                try {
                    JsonNode node = mapper.readTree(p.toFile());
                    String jobKey = node.path("jobKey").asText("");
                    String incoming = node.path("incoming").path("fileName").asText("");
                    String existingState = node.path("existing").path("state").asText("");
                    if (!jobKey.isEmpty()) {
                        rows.add(new DupRow(jobKey, incoming, existingState));
                    }
                } catch (Exception ignored) {
                    // Rapport corrompu : ignoré pour ne pas bloquer l'affichage
                }
            }
        }
        return rows;
    }

    /**
     * Écrit le fichier {@code decision.json} pour un jobKey donné.
     * Crée les dossiers intermédiaires si nécessaire.
     *
     * @param dataDir  Racine du répertoire {@code data/}.
     * @param jobKey   Clé du job doublon.
     * @param decision Décision prise par l'utilisateur.
     * @return Chemin du fichier {@code decision.json} écrit.
     * @throws IOException En cas d'erreur d'écriture.
     */
    public Path writeDecision(Path dataDir, String jobKey, DuplicateDecision decision) throws IOException {
        Path decisionPath = dataDir
                .resolve("hold")
                .resolve("duplicates")
                .resolve(jobKey)
                .resolve("decision.json");

        Files.createDirectories(decisionPath.getParent());

        Map<String, Object> payload = new HashMap<>();
        payload.put("action", decision.name());
        if (decision == DuplicateDecision.FORCE_REPROCESS) {
            payload.put("nonce", UUID.randomUUID().toString());
        }

        mapper.writerWithDefaultPrettyPrinter().writeValue(decisionPath.toFile(), payload);
        return decisionPath;
    }
}

