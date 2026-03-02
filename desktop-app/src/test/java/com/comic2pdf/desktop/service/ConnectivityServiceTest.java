package com.comic2pdf.desktop.service;

import com.comic2pdf.desktop.client.OrchestratorClient;
import com.comic2pdf.desktop.model.JobRow;
import org.junit.jupiter.api.*;

import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests unitaires de {@link ConnectivityService} — risque R4 (thread-safety).
 *
 * <p>Pas de JavaFX runtime requis : {@link ConnectivityService#isOnline()} utilise
 * un {@link AtomicBoolean} interne, lisible depuis n'importe quel thread sans
 * violation du modèle de threading JavaFX.</p>
 *
 * <p>Pas de Mockito : stub inline de {@link OrchestratorClient}.</p>
 */
@DisplayName("ConnectivityService")
class ConnectivityServiceTest {

    /** Stub minimal d'OrchestratorClient — ne fait aucun appel réseau. */
    private static OrchestratorClient stubClient() {
        return new OrchestratorClient("http://stub-no-network:0") {
            @Override
            public List<JobRow> getJobsOrThrow() {
                return List.of();
            }
        };
    }

    // -----------------------------------------------------------------------
    // État initial
    // -----------------------------------------------------------------------

    @Test
    @DisplayName("isOnline() retourne true par défaut (AtomicBoolean)")
    void isOnlineParDefaut() {
        ConnectivityService svc = new ConnectivityService(stubClient());
        try {
            assertTrue(svc.isOnline(), "isOnline() doit être true par défaut");
        } finally {
            svc.shutdown();
        }
    }

    // -----------------------------------------------------------------------
    // Thread-safety : lecture depuis un thread non-FX (R4)
    // -----------------------------------------------------------------------

    @Test
    @DisplayName("isOnline() lisible depuis un thread non-FX sans exception (R4)")
    void isOnlineThreadSafe() throws InterruptedException {
        ConnectivityService svc = new ConnectivityService(stubClient());
        AtomicBoolean result = new AtomicBoolean(false);
        AtomicBoolean threw  = new AtomicBoolean(false);
        CountDownLatch latch  = new CountDownLatch(1);

        Thread t = new Thread(() -> {
            try {
                result.set(svc.isOnline());
            } catch (Exception e) {
                threw.set(true);
            } finally {
                latch.countDown();
            }
        }, "test-non-fx-thread");
        t.setDaemon(true);
        t.start();

        assertTrue(latch.await(2, TimeUnit.SECONDS),
                "Le thread non-FX doit se terminer en < 2s");
        assertFalse(threw.get(),
                "isOnline() ne doit pas lever d'exception depuis un thread non-FX");
        assertTrue(result.get(),
                "isOnline() doit retourner true depuis un thread non-FX");
        svc.shutdown();
    }

    // -----------------------------------------------------------------------
    // Cycle de vie
    // -----------------------------------------------------------------------

    @Test
    @DisplayName("shutdown() est idempotent (double appel sans exception)")
    void shutdownIdempotent() {
        ConnectivityService svc = new ConnectivityService(stubClient());
        svc.shutdown();
        assertDoesNotThrow(svc::shutdown, "shutdown() doit être idempotent");
    }

    @Test
    @DisplayName("setOnComeOnline() accepte null sans crash")
    void setOnComeOnlineNull() {
        ConnectivityService svc = new ConnectivityService(stubClient());
        assertDoesNotThrow(() -> svc.setOnComeOnline(null));
        svc.shutdown();
    }
}
