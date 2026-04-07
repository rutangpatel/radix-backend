from dotenv import load_dotenv
import os
from imagekitio import ImageKit

load_dotenv()

imagekit = ImageKit(
    private_key = os.getenv("IMAGKIT_PRIVATE_KEY")
)

def delete(file_id):
    try:
        imagekit.files.delete(file_id)
        return {"status": "Successfull"}
    except:
        return {"status": "Unsuccessfull"}