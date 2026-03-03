package com.comic2pdf.desktop.ui;

import org.junit.jupiter.api.extension.ExtendWith;
import org.testfx.framework.junit5.ApplicationTest;

/**
 * Ancre sémantique pour tous les tests UI TestFX.
 *
 * <p>Cette classe est intentionnellement vide (aucun champ, aucune méthode).
 * Son rôle est double :</p>
 * <ol>
 *   <li><strong>Point d'héritage commun</strong> : toutes les classes de test UI
 *       étendent {@code BaseUiTest} au lieu de {@code ApplicationTest} directement,
 *       ce qui permet d'ajouter des comportements transverses sans toucher
 *       aux tests existants.</li>
 *   <li><strong>Hook d'extension JUnit 5</strong> : l'annotation
 *       {@code @ExtendWith(ScreenshotExtension.class)} est héritée automatiquement
 *       par toutes les sous-classes ({@code MainAppUiTest}, {@code JobsUiTest},
 *       {@code DuplicatesUiTest}, {@code ConfigUiTest}), activant la capture de
 *       screenshot en cas d'échec sans aucune modification requise dans ces tests.</li>
 * </ol>
 *
 * <p>La capture de screenshot est gérée par {@link ScreenshotExtension} :
 * {@code Platform.runLater} + {@code CompletableFuture} pour l'accès au FX thread,
 * sortie dans {@code target/test-screenshots/ClassName_methodName_timestamp.png}.</p>
 *
 * <p>Usage : hériter de cette classe et implémenter {@code start(Stage)}.</p>
 */
@ExtendWith(ScreenshotExtension.class)
public abstract class BaseUiTest extends ApplicationTest {
}
