"""EfficientNetV2-S livestock disease classifier → TFLite int8 (<12MB). Target: >85% top-3."""
import tensorflow as tf, mlflow
from pathlib import Path
CLASSES=14; IMG=224; BS=16; EPOCHS=60; NAME="livestock_vision_v1"

def build(n):
    base=tf.keras.applications.EfficientNetV2S(input_shape=(IMG,IMG,3),include_top=False,weights="imagenet")
    for l in base.layers[:-50]: l.trainable=False
    x=tf.keras.layers.GlobalAveragePooling2D()(base.output)
    x=tf.keras.layers.BatchNormalization()(x); x=tf.keras.layers.Dropout(0.4)(x)
    x=tf.keras.layers.Dense(256,activation="relu")(x); x=tf.keras.layers.Dropout(0.3)(x)
    return tf.keras.Model(base.input,tf.keras.layers.Dense(n,activation="softmax")(x))

def train(data_dir,output_dir):
    mlflow.set_tracking_uri("http://localhost:5050")
    with mlflow.start_run(run_name=NAME):
        aug=tf.keras.Sequential([tf.keras.layers.RandomFlip("horizontal"),tf.keras.layers.RandomRotation(0.15),tf.keras.layers.RandomBrightness(0.2)])
        norm=tf.keras.layers.Rescaling(1./255)
        tr=tf.keras.utils.image_dataset_from_directory(f"{data_dir}/train",image_size=(IMG,IMG),batch_size=BS)
        vl=tf.keras.utils.image_dataset_from_directory(f"{data_dir}/val",  image_size=(IMG,IMG),batch_size=BS)
        tr=tr.map(lambda x,y:(aug(norm(x),training=True),y)); vl=vl.map(lambda x,y:(norm(x),y))
        model=build(CLASSES)
        model.compile(optimizer=tf.keras.optimizers.AdamW(1e-4),loss="sparse_categorical_crossentropy",metrics=["accuracy",tf.keras.metrics.SparseTopKCategoricalAccuracy(k=3,name="top3")])
        h=model.fit(tr,validation_data=vl,epochs=EPOCHS,callbacks=[tf.keras.callbacks.EarlyStopping(patience=12,restore_best_weights=True)])
        top3=max(h.history["val_top3"]); assert top3>=0.85,f"top3={top3:.2%} < 85% gate"
        Path(output_dir).mkdir(parents=True,exist_ok=True)
        conv=tf.lite.TFLiteConverter.from_keras_model(model); conv.optimizations=[tf.lite.Optimize.DEFAULT]
        tfl=conv.convert(); out=f"{output_dir}/{NAME}.tflite"; open(out,"wb").write(tfl)
        assert len(tfl)/1e6<12; print(f"Exported {out} ({len(tfl)/1e6:.1f}MB)"); mlflow.log_artifact(out)

if __name__=="__main__":
    import sys; train(sys.argv[1],sys.argv[2])
