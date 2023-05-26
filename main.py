from fastapi import FastAPI, Depends, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi import Request
from config import settings
import typing as t
import uvicorn
import os
import requests
from qdrant_client import QdrantClient


from qdrant_engine import QdrantIndex
# from sentence_transformers import SentenceTransformer

app = FastAPI(
    title="DrQA backend API", docs_url="/docs"
)

origins = [
    "http://localhost:8000",
    "http://localhost:3000",
    "http://127.0.0.1:8000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)




# Load embedding model
# embedding_model = SentenceTransformer('sentence-transformers/all-mpnet-base-v2', device='cpu')

# Load the Qdrant index
qdrant_index = QdrantIndex(settings.qdrant_host, settings.qdrant_api_key, False)



class UserQuery(BaseModel):
    query: str


qdrant_client = QdrantClient(
    settings.qdrant_host, 
    prefer_grpc=False,
    api_key=settings.qdrant_api_key,
)

@app.get("/getFarmacias")
async def getFarmacias():
    url = 'https://midas.minsal.cl/farmacia_v2/WS/getLocalesTurnos.php'
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            print(data)
            return data
        else:
            print(f'Error al obtener los datos. Código de respuesta: {response.status_code}')
    except requests.exceptions.RequestException as e:
        print(f'Error de conexión: {e}')

    return None

@app.get("/")
async def root(request: Request):
    return {"message": "Server is up and running!!!"}

@app.get("/ping")
async def ping():
    return {"status": 200}

@app.get("/get-info-collection")
async def getInfoCollection():
    print("Solicitud de colecciones Qdrant")
    colecciones = qdrant_client.get_collections()
    coleccion_info = qdrant_client.get_collection(collection_name="qa_collection")
    print(coleccion_info)
    print(colecciones)
    return {"colecciones": colecciones, "coleccion_info": coleccion_info}



@app.post("/upload-file")
async def upload_file(request: Request, file: UploadFile):
    print("hello world")
    filename = file.filename
    status = "success"
    print(file.size)
    try:
        """ filepath = os.path.join('app','documents', os.path.basename(filename)) """
        filepath = os.path.join(os.path.basename(filename))
        contents = await file.read()
        with open(filepath, 'wb') as f:
            f.write(contents)
        
        qdrant_index.insert_into_index(filepath, filename)
        
    except Exception as ex:
        print("ERROR")
        print(str(ex))
        status = "error"
        if filepath is not None and os.path.exists(filepath):
            os.remove(filepath)
        # raise HTTPException(status_code=500, detail="Your file received but couldn't be stored!")

    if filepath is not None and os.path.exists(filepath):
        os.remove(filepath)
    return {"filename": filename, "status": status}
    


@app.post("/query")
async def query_index(request: Request, input_query: UserQuery):
    print(input_query)
    generated_response, relevant_docs = qdrant_index.generate_response(question=input_query.query)
    print(generated_response)
    return {"response": generated_response, "relevant_docs": relevant_docs}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", reload=True, port=8000)