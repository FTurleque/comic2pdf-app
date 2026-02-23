package com.fturleque.comic2pdf.desktop;

import javafx.application.Application;
import javafx.scene.Scene;
import javafx.stage.Stage;

public class MainApp extends Application {
    @Override
    public void start(Stage stage) {
        var root = new MainView();
        var scene = new Scene(root, 1000, 650);
        stage.setTitle("Comic2PDF - Desktop");
        stage.setScene(scene);
        stage.show();
    }

    public static void main(String[] args) {
        launch(args);
    }
}
