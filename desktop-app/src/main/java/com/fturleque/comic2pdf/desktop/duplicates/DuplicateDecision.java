package com.fturleque.comic2pdf.desktop.duplicates;

/**
 * Actions disponibles pour résoudre un doublon détecté.
 */
public enum DuplicateDecision {
    /** Réutiliser le PDF déjà produit pour ce jobKey. */
    USE_EXISTING_RESULT,
    /** Ignorer et supprimer le fichier entrant. */
    DISCARD,
    /** Forcer un retraitement complet avec un nouveau nonce. */
    FORCE_REPROCESS
}

