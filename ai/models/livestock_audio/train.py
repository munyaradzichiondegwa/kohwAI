"""Mel-spectrogram CNN audio classifier → TFLite int8 (<3MB). Target: >75% accuracy."""
import tensorflow as tf, mlflow
from pathlib import Path
CLASSES=["healthy","bovine_respiratory","newcastle_disease","other_respiratory"]; N_MELS=64; NAME="livestock_audio_v1"

def build(n):
    inp=tf.keras.Input(shape=(N_MELS,None,1))
    x=tf.keras.layers.Conv2D(32,(3,3),activation="relu",padding="same")(inp); x=tf.keras.layers.MaxPooling2D((2,2))(x)
    x=tf.keras.layers.Conv2D(64,(3,3),activation="relu",padding="same")(x);  x=tf.keras.layers.MaxPooling2D((2,2))(x)
    x=tf.keras.layers.GlobalAveragePooling2D()(x); x=tf.keras.layers.Dense(64,activation="relu")(x); x=tf.keras.layers.Dropout(0.3)(x)
    return tf.keras.Model(inp,tf.keras.layers.Dense(n,activation="softmax")(x))

def train(data_dir,output_dir):
    # TODO: load .wav files → mel-spectrograms via librosa, build tf.data.Dataset
    mlflow.set_tracking_uri("http://localhost:5050")
    with mlflow.start_run(run_name=NAME):
        model=build(len(CLASSES)); model.compile(optimizer="adam",loss="sparse_categorical_crossentropy",metrics=["accuracy"])
        Path(output_dir).mkdir(parents=True,exist_ok=True)
        conv=tf.lite.TFLiteConverter.from_keras_model(model); conv.optimizations=[tf.lite.Optimize.DEFAULT]
        tfl=conv.convert(); out=f"{output_dir}/{NAME}.tflite"; open(out,"wb").write(tfl)
        assert len(tfl)/1e6<3; print(f"Exported {out} ({len(tfl)/1e6:.1f}MB)")

if __name__=="__main__":
    import sys; train(sys.argv[1],sys.argv[2])
