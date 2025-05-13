from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold # For safety settings
from google.generativeai import GenerativeModel # Ensure correct import

from backend.models.user import User
# from backend.models.report import ReportSummary, ReportResponse # Not directly used here
from backend.auth.dependencies import get_current_user
# from backend.database import supabase # Not directly used here
from backend.config.settings import settings
import os
import shutil

router = APIRouter(prefix="/chat", tags=["chat"])

# Configure Gemini API Key at the module level
if settings.GOOGLE_API_KEY:
    genai.configure(api_key=settings.GOOGLE_API_KEY)
else:
    # This case should ideally be caught by settings validation,
    # but as a safeguard for the router:
    print("Warning: GOOGLE_API_KEY not configured. Chat routes may not function.")

# Pydantic models for request/response
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    file_uri: Optional[str] = None
    history: Optional[List[ChatMessage]] = []
    # Add a session_id if you want to maintain distinct chat sessions for a user
    # session_id: Optional[str] = None 

class ChatResponse(BaseModel):
    response: str

class UploadResponse(BaseModel):
    file_uri: str
    display_name: str


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, current_user: User = Depends(get_current_user)):
    if not settings.GOOGLE_API_KEY:
        raise HTTPException(status_code=503, detail="Gemini API not configured.")
    try:
        # Prepare chat history for Gemini
        gemini_history = []
        if request.history:
            for msg in request.history:
                role = "user" if msg.role == "user" else "model"
                gemini_history.append({"role": role, "parts": [{"text": msg.content}]})
        
        # Initialize Gemini model
        # Consider making safety_settings configurable if needed
        safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }
        # Using "gemini-1.5-flash" as a common and capable model.
        # You had "gemini-2.0-flash", ensure this model name is available to you.
        # If "gemini-2.0-flash" is correct and available, use that.
        model = GenerativeModel("gemini-2.5-flash-preview-04-17", safety_settings=safety_settings) 
        
        # Start chat session
        # If you add session_id to ChatRequest, you might manage chat instances differently,
        # e.g., storing them in memory or a database associated with session_id.
        # For now, each call starts a new chat or continues based on passed history.
        chat_session = model.start_chat(history=gemini_history)
        
        # Prepare content parts: message and optional file
        content_parts = [{"text": request.message}]
        
        if request.file_uri:
            try:
                # The file_uri from genai.upload_file is typically the name (e.g., "files/your-file-id")
                # genai.get_file needs just the name part.
                file_name = request.file_uri.split("/")[-1]
                uploaded_file = genai.get_file(name=f"files/{file_name}") # Ensure "files/" prefix if needed by API
                
                # Create a FileDataPart for the Gemini API
                # Note: The exact way to reference an existing file in a chat prompt
                # can vary slightly based on Gemini API updates.
                # The common way is to include its resource name or a specific part object.
                # For multimodal prompts, you often pass the file object directly.
                # Let's assume we pass the retrieved file object.
                content_parts.append(uploaded_file) # This might need to be wrapped, e.g. Part.from_uri or similar
                                                    # depending on how `send_message` expects file references.
                                                    # For gemini-1.5-flash, sending the file object from get_file should work.

            except Exception as e:
                # Log the error for more details
                print(f"Error retrieving file from Gemini: {e}")
                raise HTTPException(status_code=400, detail=f"Invalid or inaccessible file URI: {request.file_uri}. Error: {str(e)}")
        
        # Send message to Gemini
        # The `content_parts` list will be automatically handled by `send_message`
        response = await chat_session.send_message_async(content_parts)
        return ChatResponse(response=response.text)
    except Exception as e:
        # Log the full exception for debugging
        print(f"Chat error: {type(e).__name__} - {str(e)}")
        # Consider more specific error handling for API errors vs. other errors
        if "API key not valid" in str(e):
             raise HTTPException(status_code=401, detail="Gemini API key is invalid.")
        raise HTTPException(status_code=500, detail=f"Chat processing error: {str(e)}")

# PDF upload endpoint
@router.post("/upload-pdf", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    if not settings.GOOGLE_API_KEY:
        raise HTTPException(status_code=503, detail="Gemini API not configured.")
    try:
        # Validate file type
        if not file.filename.endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

        # Ensure temp upload directory exists (using settings for path)
        upload_dir = settings.TEMP_STORAGE_PATH
        os.makedirs(upload_dir, exist_ok=True) # TEMP_STORAGE_PATH should be defined in settings

        # Sanitize filename to prevent directory traversal or other issues
        safe_filename = os.path.basename(file.filename)
        if not safe_filename: # Handle empty or malicious filenames
            raise HTTPException(status_code=400, detail="Invalid filename.")
        file_path = os.path.join(upload_dir, safe_filename)
        
        # Save file temporarily
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Upload PDF to Gemini File API
        # display_name is optional but good practice
        gemini_file = genai.upload_file(path=file_path, display_name=safe_filename)
        
        # Clean up the temporary file
        os.remove(file_path)

        # The gemini_file.uri is often just the resource name like "files/your-file-id"
        # The gemini_file.name is the full resource name (e.g. "files/...")
        return UploadResponse(file_uri=gemini_file.name, display_name=gemini_file.display_name)
    except Exception as e:
        # Log the full exception for debugging
        print(f"PDF upload error: {type(e).__name__} - {str(e)}")
        if os.path.exists(file_path): # Attempt cleanup if file still exists
            try:
                os.remove(file_path)
            except Exception as cleanup_e:
                print(f"Error cleaning up temp file {file_path}: {cleanup_e}")
        if "API key not valid" in str(e):
             raise HTTPException(status_code=401, detail="Gemini API key is invalid.")
        raise HTTPException(status_code=500, detail=f"PDF upload error: {str(e)}")