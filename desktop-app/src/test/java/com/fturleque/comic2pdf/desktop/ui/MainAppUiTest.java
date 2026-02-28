package com.fturleque.comic2pdf.desktop.ui;

import javafx.scene.control.TabPane;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;
import org.testfx.framework.junit5.ApplicationTest;
import org.testfx.util.WaitForAsyncUtils;
import javafx.stage.Stage;

import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Test UI : vérifie que les 3 onglets (Doublons / Jobs / Configuration) sont présents
 * et accessibles via leurs IDs stables.
 *
 * <p>Note TestFX JUnit 5 : {@code start()} est appelé AVANT {@code @BeforeEach}.
 * Les overrides sont donc initialisés dans {@code @BeforeAll} (statique).</p>
 */
@Tag("ui")
class MainAppUiTest extends ApplicationTest {

    @BeforeAll
    static void setup() {
        TestableMainApp.jobsAutoRefreshOverride = false;
    }

    @Override
    public void start(Stage stage) {
        new TestableMainApp().start(stage);
    }

    @AfterAll
    static void tearDown() {
        TestableMainApp.resetOverrides();
    }

    @Test
    @DisplayName("Les 3 onglets Doublons / Jobs / Configuration sont présents et identifiables")
    void troisOngletsPresents() {
        WaitForAsyncUtils.waitForFxEvents();

        TabPane tabs = lookup("#mainTabs").query();
        assertNotNull(tabs, "#mainTabs doit exister dans la scène");
        assertEquals(3, tabs.getTabs().size(), "Exactement 3 onglets attendus");

        assertNotNull(lookup("#tabDuplicates").query(), "#tabDuplicates manquant");
        assertNotNull(lookup("#tabJobs").query(), "#tabJobs manquant");
        assertNotNull(lookup("#tabConfig").query(), "#tabConfig manquant");
    }
}

