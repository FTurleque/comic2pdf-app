package com.comic2pdf.desktop;

import javafx.beans.property.SimpleStringProperty;
import javafx.beans.property.StringProperty;

public class DupRow {
    private final StringProperty jobKey = new SimpleStringProperty();
    private final StringProperty incomingFile = new SimpleStringProperty();
    private final StringProperty existingState = new SimpleStringProperty();

    public DupRow(String jobKey, String incomingFile, String existingState) {
        this.jobKey.set(jobKey);
        this.incomingFile.set(incomingFile);
        this.existingState.set(existingState);
    }

    public String getJobKey() { return jobKey.get(); }
    public StringProperty jobKeyProperty() { return jobKey; }

    public String getIncomingFile() { return incomingFile.get(); }
    public StringProperty incomingFileProperty() { return incomingFile; }

    public String getExistingState() { return existingState.get(); }
    public StringProperty existingStateProperty() { return existingState; }
}

