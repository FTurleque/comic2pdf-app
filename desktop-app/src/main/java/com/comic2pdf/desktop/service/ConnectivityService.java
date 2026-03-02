package com.comic2pdf.desktop.service;

import com.comic2pdf.desktop.client.OrchestratorClient;
import javafx.application.Platform;
import javafx.beans.property.BooleanProperty;
import javafx.beans.property.SimpleBooleanProperty;
import javafx.beans.property.SimpleStringProperty;
import javafx.beans.property.StringProperty;

import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * Service de connectivité vers l'orchestrateur.
 *
 * <p>Maintient un {@link BooleanProperty} {@code online} observable par l'UI.
 * Quand offline, un ping léger toutes les {@value #PING_INTERVAL_SECONDS} secondes
 * tente la reconnexion automatique.</p>
 *
 * <h2>Thread-safety (R4)</h2>
 * <p>Le scheduler daemon ne lit ni ne mute aucune Property JavaFX directement.
 * L'état offline est maintenu dans {@code offlineFlag} ({@link AtomicBoolean} thread-safe).
 * {@link #markOnline()} et {@link #markOffline(String)} se reroutent automatiquement
 * via {@code Platform.runLater()} si appelés hors du FX thread.</p>
 */
public class ConnectivityService {

    private static final long PING_INTERVAL_SECONDS = 15;

    private final BooleanProperty online        = new SimpleBooleanProperty(true);
    private final StringProperty  offlineReason = new SimpleStringProperty("");

    /**
     * Flag thread-safe lu par le scheduler daemon.
     * Évite toute lecture de {@link BooleanProperty} JavaFX hors du FX thread.
     */
    private final AtomicBoolean offlineFlag = new AtomicBoolean(false);

    private final OrchestratorClient       client;
    private final ScheduledExecutorService scheduler;
    private volatile Runnable onComeOnline;

    /**
     * Construit le service avec le client HTTP fourni.
     *
     * @param client Client HTTP orchestrateur (utilisé pour le ping).
     */
    public ConnectivityService(OrchestratorClient client) {
        this.client = client;
        this.scheduler = Executors.newSingleThreadScheduledExecutor(r -> {
            Thread t = new Thread(r, "connectivity-ping");
            t.setDaemon(true);
            return t;
        });
        scheduler.scheduleWithFixedDelay(
                this::ping,
                PING_INTERVAL_SECONDS, PING_INTERVAL_SECONDS, TimeUnit.SECONDS);
    }

    /** @return Propriété observable (true = en ligne). */
    public BooleanProperty onlineProperty() { return online; }

    /**
     * @return {@code true} si l'orchestrateur est considéré accessible.
     * Thread-safe : utilise {@link AtomicBoolean}, pas la {@link BooleanProperty}.
     */
    public boolean isOnline() { return !offlineFlag.get(); }

    /** @return Propriété raison d'offline, chaîne vide si en ligne. */
    public StringProperty offlineReasonProperty() { return offlineReason; }

    /**
     * Définit un callback exécuté sur le FX thread quand la connexion revient.
     *
     * @param onComeOnline Runnable appelé au retour en ligne.
     */
    public void setOnComeOnline(Runnable onComeOnline) {
        this.onComeOnline = onComeOnline;
    }

    /**
     * Marque l'orchestrateur comme accessible.
     * Se reroute automatiquement via {@code Platform.runLater()} si appelé hors du FX thread.
     */
    public void markOnline() {
        if (!Platform.isFxApplicationThread()) {
            Platform.runLater(this::markOnline);
            return;
        }
        offlineFlag.set(false);
        online.set(true);
        offlineReason.set("");
    }

    /**
     * Marque l'orchestrateur comme inaccessible avec une raison courte.
     * Se reroute automatiquement via {@code Platform.runLater()} si appelé hors du FX thread.
     *
     * @param reason Raison courte affichée dans la bannière (peut être null).
     */
    public void markOffline(String reason) {
        if (!Platform.isFxApplicationThread()) {
            final String r = reason;
            Platform.runLater(() -> markOffline(r));
            return;
        }
        offlineFlag.set(true);
        online.set(false);
        offlineReason.set(reason != null ? reason : "");
    }

    /**
     * Arrête proprement le scheduler de ping.
     * Appeler depuis {@code JobsController.stop()}.
     */
    public void shutdown() {
        scheduler.shutdownNow();
    }

    // -----------------------------------------------------------------------
    // Privé — ping daemon
    // -----------------------------------------------------------------------

    /**
     * Ping exécuté sur le thread daemon.
     * Lit uniquement {@code offlineFlag} ({@link AtomicBoolean}) — jamais de Property JavaFX.
     */
    private void ping() {
        if (!offlineFlag.get()) return; // déjà en ligne — AtomicBoolean, pas online.get()
        try {
            client.getJobsOrThrow();
            Platform.runLater(() -> {
                markOnline();
                Runnable cb = onComeOnline;
                if (cb != null) cb.run();
            });
        } catch (Exception ignored) {
            // Toujours offline — prochain tick dans PING_INTERVAL_SECONDS
        }
    }
}
