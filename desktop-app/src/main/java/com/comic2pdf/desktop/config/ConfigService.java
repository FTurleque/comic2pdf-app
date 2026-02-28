package com.comic2pdf.desktop.config;

import com.fasterxml.jackson.databind.ObjectMapper;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;

/**
 * Service de persistance de la configuration locale desktop.
 *
 * <p>Stocke {@code config.json} dans :</p>
 * <ul>
 *   <li>Windows : {@code %APPDATA%\comic2pdf\config.json}</li>
 *   <li>Autres  : {@code ~/.comic2pdf/config.json}</li>
 * </ul>
 *
 * <p>Logique de sérialisation entièrement testable (filesystem via {@code @TempDir}).</p>
 */
public class ConfigService {

    private final ObjectMapper mapper;
    private final Path configPath;

    /**
     * Construit le service avec le chemin par défaut (AppData / home).
     */
    public ConfigService() {
        this(new ObjectMapper(), resolveDefaultConfigPath());
    }

    /**
     * Construit le service avec un ObjectMapper et un chemin explicites.
     * Utile pour les tests.
     *
     * @param mapper     ObjectMapper Jackson à utiliser.
     * @param configPath Chemin complet du fichier {@code config.json}.
     */
    public ConfigService(ObjectMapper mapper, Path configPath) {
        this.mapper = mapper;
        this.configPath = configPath;
    }

    /**
     * Charge la configuration depuis le disque.
     * Si le fichier est absent ou corrompu, retourne une configuration par défaut.
     *
     * @return {@link AppConfig} chargée ou par défaut.
     */
    public AppConfig load() {
        if (!Files.exists(configPath)) {
            return new AppConfig();
        }
        try {
            return mapper.readValue(configPath.toFile(), AppConfig.class);
        } catch (Exception e) {
            return new AppConfig();
        }
    }

    /**
     * Sauvegarde la configuration sur le disque (écriture atomique via fichier temporaire).
     *
     * @param config Configuration à sauvegarder.
     * @throws IOException En cas d'erreur d'écriture.
     */
    public void save(AppConfig config) throws IOException {
        Files.createDirectories(configPath.getParent());
        Path tmp = configPath.resolveSibling(configPath.getFileName() + ".tmp");
        mapper.writerWithDefaultPrettyPrinter().writeValue(tmp.toFile(), config);
        Files.move(tmp, configPath, java.nio.file.StandardCopyOption.REPLACE_EXISTING);
    }

    /**
     * Retourne le chemin du fichier de configuration.
     *
     * @return Chemin absolu du fichier {@code config.json}.
     */
    public Path getConfigPath() {
        return configPath;
    }

    // -----------------------------------------------------------------------
    // Helpers
    // -----------------------------------------------------------------------

    /**
     * Résout le chemin par défaut du fichier de configuration selon l'OS.
     *
     * @return Chemin vers {@code config.json} dans le dossier utilisateur.
     */
    private static Path resolveDefaultConfigPath() {
        String appData = System.getenv("APPDATA");
        if (appData != null && !appData.isBlank()) {
            return Paths.get(appData, "comic2pdf", "config.json");
        }
        return Paths.get(System.getProperty("user.home"), ".comic2pdf", "config.json");
    }
}

