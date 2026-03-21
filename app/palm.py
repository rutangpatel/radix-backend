import cv2
import numpy as np
import tensorflow as tf
from PIL import Image
import io

def preprocess_image(image_bytes: bytes):
    #For Direct Image received
    np_arr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    
    #BGR -> RGB
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    #Resizing the image and then converting it into array of float32
    img = cv2.resize(img, (224, 224))
    img = img.astype(np.float32)

    #Preprocessing of the image by specific resnet
    img = tf.keras.applications.resnet50.preprocess_input(img)
    
    #Adding the batch dimension
    img = np.expand_dims(img, axis = 0)
    return img

def build_embedding_model():
    base = tf.keras.applications.ResNet50(
        include_top = False,
        weights = "imagenet",
        input_shape = (224, 224, 3),
        pooling = "avg"
    )
    base.trainable = False

    inputs = tf.keras.Input(shape = (224, 224, 3))
    x = base(inputs, training = False)
    x = tf.keras.layers.Dense(512)(x)
    x = tf.keras.layers.BatchNormalization()(x)
    x = tf.keras.layers.Lambda(
        lambda t: tf.math.l2_normalize(t, axis = 1)
    )(x)

    model = tf.keras.Model(inputs, x, name = "palm_embedder")
    return model

embedding_model = build_embedding_model()

def get_embedding(image_bytes: bytes):
    img = preprocess_image(image_bytes)
    embedding = embedding_model.predict(img, verbose = 0)
    return embedding.astype("float32")

def get_averaged_embedding(list):
    embeddings = []
    for image_bytes in list:
        emb = get_embedding(image_bytes)
        embeddings.append(emb)
    
    avg = np.mean(embeddings, axis = 0)
    avg = avg / np.linalg.norm(avg)
    return avg.astype("float32")