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

/**
 * Service de connectivité vers l'orchestrateur.
 *
 * <p>Maintient un {@link BooleanProperty} {@code online} observable par l'UI.
 * Quand offline, un ping léger toutes les 15 secondes tente la reconnexion.</p>
 *
 * <p><b>Thread-safety :</b> toute mutation des propriétés JavaFX passe
 * exclusivement par {@code Platform.runLater()}. Les assertions de debug
 * (activées avec {@code -ea}) valident le thread appelant.</p>
 */
public class ConnectivityService {

    private static final long PING_INTERVAL_SECONDS = 15;

    private final BooleanProperty online        = new SimpleBooleanProperty(true);
    private final StringProperty  offlineReason = new SimpleStringProperty("");

    private final OrchestratorClient      client;
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

    /** @return true si l'orchestrateur est considéré accessible. */
    public boolean isOnline() { return online.get(); }

    /** @return Propriété raison d'offline, chaîne vide si en ligne. */
    public StringProperty offlineReasonProperty() { return offlineReason; }

    /**
     * Définit un callback exécuté sur le FX thread quand la connexion revient.
     *
     * @param onComeOnline Runnable appelé via {@code Platform.runLater} au retour en ligne.
     */
    public void setOnComeOnline(Runnable onComeOnline) {
        this.onComeOnline = onComeOnline;
    }

    /**
     * Marque l'orchestrateur comme accessible.
     * Doit être appelé uniquement depuis le FX Application Thread.
     */
    public void markOnline() {
        assert Platform.isFxApplicationThread()
                : "ConnectivityService.markOnline() appelé hors du FX thread !";
        online.set(true);
        offlineReason.set("");
    }

    /**
     * Marque l'orchestrateur comme inaccessible avec une raison courte.
     * Doit être appelé uniquement depuis le FX Application Thread.
     *
     * @param reason Raison courte affichée dans la bannière (peut être null).
     */
    public void markOffline(String reason) {
        assert Platform.isFxApplicationThread()
                : "ConnectivityService.markOffline() appelé hors du FX thread !";
        online.set(false);
        offlineReason.set(reason != null ? reason : "");
    }

    /**
     * Arrête proprement le scheduler de ping.
     * Doit être appelé depuis {@code JobsController.stop()}.
     */
    public void shutdown() {
        scheduler.shutdownNow();
    }

    // -----------------------------------------------------------------------
    // Privé — ping daemon
    // -----------------------------------------------------------------------

    /** Ping exécuté sur le thread daemon — ne touche JAMAIS les Property directement. */
    private void ping() {
        if (online.get()) return; // déjà en ligne
        try {
            client.getJobsOrThrow();
            // Succès : repasser en ligne sur le FX thread
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

