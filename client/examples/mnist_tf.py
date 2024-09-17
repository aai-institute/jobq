import json
import os
from pathlib import Path
from typing import Any

import keras
import numpy as np
import tensorflow as tf
from filelock import FileLock
from ray.air import Result, RunConfig, ScalingConfig
from ray.air.integrations.keras import ReportCheckpointCallback
from ray.train.tensorflow import TensorflowTrainer


def mnist_dataset(batch_size: int) -> tf.data.Dataset:
    with FileLock(Path.home() / ".mnist_lock"):
        (x_train, y_train), _ = keras.datasets.mnist.load_data()
    # The `x` arrays are in uint8 and have values in the [0, 255] range.
    # You need to convert them to float32 with values in the [0, 1] range.
    x_train = x_train / np.float32(255)
    y_train = y_train.astype(np.int64)
    train_dataset = (
        tf.data.Dataset.from_tensor_slices((x_train, y_train))
        .shuffle(60000)
        .repeat()
        .batch(batch_size)
    )
    return train_dataset


def build_cnn_model() -> keras.Model:
    model = keras.Sequential([
        keras.Input(shape=(28, 28)),
        keras.layers.Reshape(target_shape=(28, 28, 1)),
        keras.layers.Conv2D(32, 3, activation="relu"),
        keras.layers.Flatten(),
        keras.layers.Dense(128, activation="relu"),
        keras.layers.Dense(10),
    ])
    return model


def train_func(config: dict) -> Any:
    per_worker_batch_size = config.get("batch_size", 64)
    epochs = config.get("epochs", 3)
    steps_per_epoch = config.get("steps_per_epoch", 70)

    tf_config = json.loads(os.environ["TF_CONFIG"])
    num_workers = len(tf_config["cluster"]["worker"])

    strategy = tf.distribute.MultiWorkerMirroredStrategy()

    global_batch_size = per_worker_batch_size * num_workers
    multi_worker_dataset = mnist_dataset(global_batch_size)

    with strategy.scope():
        # Model building/compiling need to be within `strategy.scope()`.
        multi_worker_model = build_cnn_model()
        learning_rate = config.get("lr", 0.001)
        multi_worker_model.compile(
            loss=keras.losses.SparseCategoricalCrossentropy(from_logits=True),
            optimizer=keras.optimizers.SGD(learning_rate=learning_rate),
            metrics=["accuracy"],
        )

    history = multi_worker_model.fit(
        multi_worker_dataset,
        epochs=epochs,
        steps_per_epoch=steps_per_epoch,
        callbacks=[ReportCheckpointCallback()],
    )
    results = history.history
    return results


def train_tensorflow_mnist(
    num_workers: int = 2,
    use_gpu: bool = False,
    epochs: int = 4,
    storage_path: str | None = None,
) -> Result:
    config = {"lr": 1e-3, "batch_size": 64, "epochs": epochs}
    trainer = TensorflowTrainer(
        train_loop_per_worker=train_func,
        train_loop_config=config,
        scaling_config=ScalingConfig(num_workers=num_workers, use_gpu=use_gpu),
        run_config=RunConfig(storage_path=storage_path),
    )
    results = trainer.fit()
    return results
