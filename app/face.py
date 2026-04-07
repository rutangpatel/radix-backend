from deepface import DeepFace
import numpy as np

def get_embeddings(image):
    result = DeepFace.represent(image, model_name = "Facenet512", enforce_detection = True, detector_backend = "retinaface", anti_spoofing = True)
    if result[0].get("is_real") is False:
        raise ValueError("Liveness check failed — spoof detected") 
    embedding = np.array(result[0]["embedding"])  
    return embedding.tolist()

def get_average_embeddings(image_list):
    embeddings = []
    for image in image_list:
        embedding = get_embeddings(image)
        if embedding is not None:
            feat = np.array(embedding).flatten()
            embeddings.append(feat)
    
    embeddings = np.array(embeddings)
    average = np.mean(embeddings, axis = 0)
    average = average / np.linalg.norm(average)
    return average.tolist()




