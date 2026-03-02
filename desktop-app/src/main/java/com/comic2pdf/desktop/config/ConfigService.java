package com.comic2pdf.desktop.config;

import com.fasterxml.jackson.databind.ObjectMapper;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.attribute.PosixFilePermission;
import java.nio.file.attribute.PosixFilePermissions;
import java.util.Optional;
import java.util.Set;

/**
 * Service de persistance de la configuration locale desktop.
 *
 * <p>Stocke {@code config.json} dans :</p>
 * <ul>
 *   <li>Windows : {@code %APPDATA%\comic2pdf\config.json}</li>
 *   <li>Unix    : {@code ${XDG_CONFIG_HOME:-~/.config}/comic2pdf/config.json}</li>
 * </ul>
 *
 * <h2>Priorité de la clé API</h2>
 * <p>Lors du chargement, si la variable d'environnement {@code ORCHESTRATOR_API_KEY}
 * est définie et non vide, elle <b>remplace</b> la valeur lue dans {@code config.json}.
 * Cela garantit que la valeur de l'env var est toujours prioritaire (option A &gt; option B).</p>
 *
 * <h2>Permissions fichier</h2>
 * <p>Sur les systèmes POSIX, le fichier {@code config.json} est créé avec les permissions
 * {@code 600} (lecture/écriture pour l'utilisateur courant uniquement). Sur Windows,
 * cette restriction n'est pas appliquée automatiquement — la sécurité repose sur les ACL
 * du dossier {@code %APPDATA%} qui est déjà restreint à l'utilisateur courant.</p>
 */
public class ConfigService {

    /** Variable d'environnement prioritaire pour la clé API (option A). */
    private static final String ENV_API_KEY = "ORCHESTRATOR_API_KEY";

    private final ObjectMapper mapper;
    private final Path configPath;

    /**
     * Construit le service avec le chemin par défaut (AppData / XDG_CONFIG_HOME / home).
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
     *
     * <p>Règle de priorité pour la clé API :</p>
     * <ol>
     *   <li>Env var {@code ORCHESTRATOR_API_KEY} (prioritaire) — ne modifie pas le fichier.</li>
     *   <li>Champ {@code apiKey} dans {@code config.json} (fallback).</li>
     * </ol>
     *
     * <p>Si le fichier est absent ou corrompu, retourne une configuration par défaut.</p>
     *
     * @return {@link AppConfig} chargée (avec clé API résolue) ou par défaut.
     */
    public AppConfig load() {
        AppConfig cfg;
        if (!Files.exists(configPath)) {
            cfg = new AppConfig();
        } else {
            try {
                cfg = mapper.readValue(configPath.toFile(), AppConfig.class);
            } catch (Exception e) {
                cfg = new AppConfig();
            }
        }
        // Option A : env var ORCHESTRATOR_API_KEY override toujours config.json
        String envKey = System.getenv(ENV_API_KEY);
        if (envKey != null && !envKey.isBlank()) {
            cfg.setApiKey(envKey);
        }
        return cfg;
    }

    /**
     * Sauvegarde la configuration sur le disque (écriture atomique via fichier temporaire).
     *
     * <p>Si la clé API provient de l'env var, elle est stockée telle quelle dans le fichier
     * (comportement attendu : l'env var reste prioritaire au rechargement).</p>
     *
     * <p>Sur les systèmes POSIX, applique les permissions {@code 600} (best-effort).</p>
     *
     * @param config Configuration à sauvegarder.
     * @throws IOException En cas d'erreur d'écriture.
     */
    public void save(AppConfig config) throws IOException {
        Files.createDirectories(configPath.getParent());
        Path tmp = configPath.resolveSibling(configPath.getFileName() + ".tmp");
        mapper.writerWithDefaultPrettyPrinter().writeValue(tmp.toFile(), config);
        Files.move(tmp, configPath, java.nio.file.StandardCopyOption.REPLACE_EXISTING);
        applyRestrictivePermissions(configPath);
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
     * <ul>
     *   <li>Windows ({@code APPDATA} défini) : {@code %APPDATA%\comic2pdf\config.json}</li>
     *   <li>Unix ({@code XDG_CONFIG_HOME} défini) : {@code $XDG_CONFIG_HOME/comic2pdf/config.json}</li>
     *   <li>Unix (fallback) : {@code ~/.config/comic2pdf/config.json}</li>
     * </ul>
     *
     * @return Chemin vers {@code config.json} dans le dossier utilisateur.
     */
    private static Path resolveDefaultConfigPath() {
        // Windows
        String appData = System.getenv("APPDATA");
        if (appData != null && !appData.isBlank()) {
            return Paths.get(appData, "comic2pdf", "config.json");
        }
        // Unix — XDG_CONFIG_HOME ou ~/.config
        String xdgConfig = System.getenv("XDG_CONFIG_HOME");
        String configBase = (xdgConfig != null && !xdgConfig.isBlank())
                ? xdgConfig
                : Paths.get(System.getProperty("user.home"), ".config").toString();
        return Paths.get(configBase, "comic2pdf", "config.json");
    }

    /**
     * Applique des permissions restrictives ({@code rw-------} = 600) sur le fichier de config.
     * Best-effort : l'échec est ignoré silencieusement (pas de fail sur Windows ou FS non-POSIX).
     *
     * @param path Chemin du fichier à restreindre.
     */
    private static void applyRestrictivePermissions(Path path) {
        try {
            Set<PosixFilePermission> perms = PosixFilePermissions.fromString("rw-------");
            Files.setPosixFilePermissions(path, perms);
        } catch (UnsupportedOperationException | IOException ignored) {
            // Non-POSIX (Windows) ou erreur non fatale — on continue
        }
    }
}
