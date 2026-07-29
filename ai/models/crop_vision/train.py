"""
Crop pest & disease vision model training.
Target: >85% top-3 accuracy on 30+ Zimbabwean crop disease classes.
Model: MobileNetV3-Small fine-tuned → exported to TFLite int8 quantised (<10MB).
"""
import tensorflow as tf
import mlflow
from pathlib import Path

CLASSES     = 32     # Adjust to actual dataset
IMG_SIZE    = 224
BATCH_SIZE  = 32
EPOCHS      = 50
MODEL_NAME  = "crop_vision_v1"


def build_model(num_classes: int) -> tf.keras.Model:
    base = tf.keras.applications.MobileNetV3Small(
        input_shape=(IMG_SIZE, IMG_SIZE, 3), include_top=False, weights="imagenet"
    )
    base.trainable = False  # Phase 1: transfer learning
    x = tf.keras.layers.GlobalAveragePooling2D()(base.output)
    x = tf.keras.layers.Dropout(0.3)(x)
    out = tf.keras.layers.Dense(num_classes, activation="softmax")(x)
    return tf.keras.Model(base.input, out)


def train(data_dir: str, output_dir: str):
    mlflow.set_tracking_uri("http://localhost:5050")
    with mlflow.start_run(run_name=MODEL_NAME):
        # Load dataset
        train_ds = tf.keras.utils.image_dataset_from_directory(
            f"{data_dir}/train", image_size=(IMG_SIZE, IMG_SIZE), batch_size=BATCH_SIZE
        )
        val_ds = tf.keras.utils.image_dataset_from_directory(
            f"{data_dir}/val", image_size=(IMG_SIZE, IMG_SIZE), batch_size=BATCH_SIZE
        )

        # Preprocessing
        norm = tf.keras.layers.Rescaling(1.0 / 255)
        train_ds = train_ds.map(lambda x, y: (norm(x), y))
        val_ds   = val_ds.map(lambda x, y: (norm(x), y))

        model = build_model(CLASSES)
        model.compile(
            optimizer=tf.keras.optimizers.Adam(1e-3),
            loss="sparse_categorical_crossentropy",
            metrics=["accuracy", tf.keras.metrics.SparseTopKCategoricalAccuracy(k=3, name="top3_acc")],
        )

        callbacks = [
            tf.keras.callbacks.EarlyStopping(patience=10, restore_best_weights=True),
            tf.keras.callbacks.ReduceLROnPlateau(patience=5),
        ]
        history = model.fit(train_ds, validation_data=val_ds, epochs=EPOCHS, callbacks=callbacks)

        val_top3 = max(history.history["val_top3_acc"])
        mlflow.log_metrics({"val_top3_accuracy": val_top3})
        mlflow.log_param("model", MODEL_NAME)

        assert val_top3 >= 0.85, f"Top-3 accuracy {val_top3:.2%} below 85% gate — NOT deploying"

        # Export TFLite with int8 quantisation
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        converter = tf.lite.TFLiteConverter.from_keras_model(model)
        converter.optimizations = [tf.lite.Optimize.DEFAULT]
        tflite_model = converter.convert()
        tflite_path = f"{output_dir}/{MODEL_NAME}.tflite"
        with open(tflite_path, "wb") as f:
            f.write(tflite_model)
        print(f"Model exported: {tflite_path} ({len(tflite_model)/1e6:.1f}MB)")
        mlflow.log_artifact(tflite_path)


if __name__ == "__main__":
    import sys
    train(data_dir=sys.argv[1], output_dir=sys.argv[2])
