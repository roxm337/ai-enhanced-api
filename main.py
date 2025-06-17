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

def format_prompt(template: str, **kwargs) -> str:
    return template.format(**kwargs)

def gemini_response(prompt: str) -> str:
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error: {str(e)}"

def extract_text_from_file(file: UploadFile) -> str:
    content = file.file.read()
    if file.filename.endswith(".pdf"):
        with pdfplumber.open(BytesIO(content)) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)
    elif file.filename.endswith(".docx"):
        doc = docx.Document(BytesIO(content))
        return "\n".join(p.text for p in doc.paragraphs)
    else:
        return ""

# --- Endpoints ---

@app.post("/summarize")
async def summarize(request: Request, api_key: str = Depends(get_api_key)):
    data = await request.json()
    prompt = format_prompt(PROMPTS["summarize"], style=data.get("style", "simple"), text=data.get("text", ""))
    return {"summary": gemini_response(prompt)}

@app.post("/rephrase")
async def rephrase(request: Request, api_key: str = Depends(get_api_key)):
    data = await request.json()
    prompt = format_prompt(PROMPTS["rephrase"], tone=data.get("tone", "professional"), text=data.get("text", ""))
    return {"rephrased": gemini_response(prompt)}

@app.post("/extract-keywords")
async def extract_keywords(request: Request, api_key: str = Depends(get_api_key)):
    data = await request.json()
    prompt = format_prompt(PROMPTS["extract_keywords"], text=data.get("text", ""))
    return {"keywords": gemini_response(prompt)}

@app.post("/generate-quiz")
async def generate_quiz(request: Request, api_key: str = Depends(get_api_key)):
    data = await request.json()
    prompt = (
        "Generate a quiz with {count} questions based on the following text. "
        "Return the result as a JSON array of objects, each with 'number', 'question', and 'answer' fields. "
        "Text: {text}"
    ).format(count=data.get("count", 5), text=data.get("text", ""))
    raw_response = gemini_response(prompt)
    json_str = re.sub(r"^```(?:json)?\s*|```$", "", raw_response.strip(), flags=re.MULTILINE).strip()
    try:
        quiz_json = json.loads(json_str)
        return {"quiz": quiz_json}
    except Exception as e:
        return {"quiz_raw": raw_response, "error": f"Could not parse JSON from model response: {e}"}

@app.post("/explain")
async def explain(request: Request, api_key: str = Depends(get_api_key)):
    data = await request.json()
    prompt = format_prompt(PROMPTS["explain"], level=data.get("level", "beginner"), text=data.get("text", ""))
    return {"explanation": gemini_response(prompt)}

@app.post("/summarize-doc")
async def summarize_doc(file: UploadFile = File(...), style: str = "simple", api_key: str = Depends(get_api_key)):
    text = extract_text_from_file(file)
    if not text.strip():
        return {"error": "Could not extract text from file."}
    prompt = format_prompt(PROMPTS["summarize"], style=style, text=text[:8000])  # Limit to 8K chars
    return {"summary": gemini_response(prompt)}

