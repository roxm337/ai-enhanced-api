from pprint import pprint
import re
from fastapi import FastAPI, Request, HTTPException, File, UploadFile, Depends, Security, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security.api_key import APIKeyHeader
import os
import json
from dotenv import load_dotenv
import google.generativeai as genai
import pdfplumber
import docx
from io import BytesIO

load_dotenv()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure Gemini API key
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.0-flash-lite")

# Load prompt templates
with open("prompts_library.json", "r") as f:
    PROMPTS = json.load(f)

# API key auth setup
api_key_header = APIKeyHeader(name="x-api-key", auto_error=False)

async def get_api_key(api_key: str = Security(api_key_header)):
    expected_key = os.getenv("FASTAPI_API_KEY")
    if not api_key or api_key != expected_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key",
        )
    return api_key

@app.get("/")
async def root():
    return {"message": "Welcome to the Gemini API integration!"}

