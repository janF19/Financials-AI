from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold # For safety settings
from google.generativeai import GenerativeModel
from google.generativeai.types import GenerationConfig # For max_output_tokens
from google.ai.generativelanguage_v1beta.types.file import File as GapicFile # Import for File.State enum



from backend.models.user import User
# from backend.models.report import ReportSummary, ReportResponse # Not directly used here
from backend.auth.dependencies import get_current_user
# from backend.database import supabase # Not directly used here
from backend.config.settings import settings
from backend.utils.usage_limiter import check_and_increment_api_usage, get_token_usage_status, update_user_token_usage # Import new functions
import os
import shutil
import logging


logger = logging.getLogger(__name__)

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
        # --- Token Usage Check (Part 1: Get current status) ---
        user_db_id, current_token_usage, user_token_limit, month_start_iso = get_token_usage_status(current_user)

        # Prepare chat history for Gemini API (list of dicts)
        gemini_api_history = []
        if request.history:
            for msg in request.history:
                role = "user" if msg.role == "user" else "model"
                gemini_api_history.append({"role": role, "parts": [{"text": msg.content}]})
        
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
        
        # Start chat session with the prepared history
        chat_session = model.start_chat(history=gemini_api_history)
        
        # Prepare content parts for the current message: text and optional file
        current_message_content_parts = [{"text": request.message}] # Start with the text part
        
        uploaded_gemini_file_object = None 
        if request.file_uri:
            try:
                file_name_for_get = request.file_uri # This should be "files/your-file-id"
                logger.info(f"Attempting to retrieve file with name: {file_name_for_get}")
                uploaded_gemini_file_object = genai.get_file(name=file_name_for_get)
                
                logger.info(f"Retrieved file: Name: {uploaded_gemini_file_object.name}, Display Name: {uploaded_gemini_file_object.display_name}, MIME Type: {uploaded_gemini_file_object.mime_type}, State: {uploaded_gemini_file_object.state}, URI: {uploaded_gemini_file_object.uri}")

                if uploaded_gemini_file_object.state != GapicFile.State.ACTIVE:  
                    logger.error(f"Retrieved file '{uploaded_gemini_file_object.name}' (State: {uploaded_gemini_file_object.state}) is not in ACTIVE state ({GapicFile.State.ACTIVE}). Cannot use for chat.")
                    logger.info(f"Retrieved file: Name: {uploaded_gemini_file_object.name}, Display Name: {uploaded_gemini_file_object.display_name}, MIME Type: {uploaded_gemini_file_object.mime_type}, State: {uploaded_gemini_file_object.state}, URI: {uploaded_gemini_file_object.uri}")

                    raise HTTPException(status_code=400, detail=f"File {uploaded_gemini_file_object.display_name} is still processing or in an error state. Current state: {uploaded_gemini_file_object.state}. Please try again later.")

                # Use the File object directly in content parts
                
                current_message_content_parts = [
                    {"text": request.message},
                    uploaded_gemini_file_object  # If the SDK expects the file object directly
                ]
                logger.info(f"Appended file directly to content parts not using URI: {uploaded_gemini_file_object.uri}")
                
                
                
                #current_message_content_parts.append(uploaded_gemini_file_object)
                #logger.info(f"Appended file as Part to content_parts using URI: {uploaded_gemini_file_object.uri}")

            except Exception as e:
                logger.error(f"Error retrieving or preparing file from Gemini: {e}", exc_info=True)
                raise HTTPException(status_code=400, detail=f"Invalid or inaccessible file URI '{request.file_uri}'. Error: {str(e)}")
        
        # --- Token Usage Check (Part 2: Pre-check input tokens) ---
        try:
            # Construct the full conversation content for token counting.
            # Each item in this list should represent a full "Content" object (turn).
            contents_for_token_counting = []
            
            # Add past history
            contents_for_token_counting.extend(gemini_api_history) # gemini_api_history is already List[Content-like dict]
            
            # Add current user message (with potential file) as the latest Content object
            # The `current_message_content_parts` is a list of parts for the current turn.
            contents_for_token_counting.append({
                "role": "user", # Current message is from the user
                "parts": current_message_content_parts
            })
            
            prompt_tokens_count = model.count_tokens(contents_for_token_counting).total_tokens
        except Exception as e:
            logger.error(f"Error counting tokens for user {current_user.email}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Could not estimate request token size.")

        if current_token_usage + prompt_tokens_count > user_token_limit:
            logger.warning(f"User {current_user.email} (ID: {user_db_id}) would exceed token limit. Current: {current_token_usage}, Prompt: {prompt_tokens_count}, Limit: {user_token_limit}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Processing this request would exceed your monthly token limit of {user_token_limit}. "
                       f"You have {user_token_limit - current_token_usage} tokens remaining this month. This request requires approximately {prompt_tokens_count} input tokens."
            )
        
        # Configure generation settings, including max_output_tokens
        generation_config = GenerationConfig(
            max_output_tokens=settings.MAX_OUTPUT_TOKENS_GEMINI
            # You can add other parameters like temperature, top_p, top_k here if needed
            # temperature=0.7,
            # top_p=1.0,
            # top_k=32,
        )

        # Send message to Gemini
        # The `current_message_content_parts` is what we send for the current turn.
        # The history is managed by the chat_session.
        response = await chat_session.send_message_async(current_message_content_parts, generation_config=generation_config)
        
        # --- API Call Count and Token Usage Update (Part 3: Post-call update) ---
        # Increment API call count (do this only on successful Gemini interaction)
        #check_and_increment_api_usage(current_user)

        # --- Enhanced Logging for Gemini Response ---
        generated_text = "" # Initialize a variable to hold the final text

        if response.prompt_feedback:
            logger.warning(f"Gemini prompt feedback for user {current_user.email} (ID: {user_db_id}): {response.prompt_feedback}")
        
        if not response.candidates:
            logger.warning(f"Gemini returned NO CANDIDATES for user {current_user.email} (ID: {user_db_id}). Full response object (may be large): {response}")
        else:
            logger.info(f"Gemini returned {len(response.candidates)} candidate(s) for user {current_user.email} (ID: {user_db_id}).")
            first_candidate = response.candidates[0]
            # Log candidate details, including finish_reason and safety_ratings
            candidate_token_count_attr = getattr(first_candidate, 'token_count', 'N/A') # Handle if token_count is not present
            logger.info(
                f"First candidate details for user {current_user.email} (ID: {user_db_id}): "
                f"Finish reason: {first_candidate.finish_reason}, "
                f"Safety ratings: {first_candidate.safety_ratings}, "
                f"Token count: {candidate_token_count_attr}"
            )
            
            # Attempt to get text from the first candidate's content parts
            if first_candidate.content and first_candidate.content.parts:
                # Ensure part.text exists and is not None before joining
                candidate_text_parts = [part.text for part in first_candidate.content.parts if hasattr(part, 'text') and part.text is not None]
                generated_text = "".join(candidate_text_parts)
                
                if not generated_text:
                    logger.warning(
                        f"Extracted empty text from first candidate's parts for user {current_user.email} (ID: {user_db_id}). "
                        f"Original parts (or their types): {[type(p) for p in first_candidate.content.parts]}. "
                        f"Finish reason: {first_candidate.finish_reason}. "
                        f"Prompt: '{request.message[:100]}...', File URI: {request.file_uri}"
                    )
                else:
                    logger.info(f"Text extracted directly from first candidate parts for user {current_user.email} (ID: {user_db_id}): '{generated_text[:200]}...' (length: {len(generated_text)})")
            else:
                logger.warning(
                    f"First candidate for user {current_user.email} (ID: {user_db_id}) has no content or no parts. "
                    f"Finish reason: {first_candidate.finish_reason}. Candidate content: {first_candidate.content}. "
                    f"Prompt: '{request.message[:100]}...', File URI: {request.file_uri}"
                )

            # Fallback to response.text if direct extraction fails or is empty, but log it
            if not generated_text and hasattr(response, 'text'):
                logger.info(f"Direct candidate text extraction was empty for user {current_user.email} (ID: {user_db_id}), falling back to response.text which is: '{response.text[:200]}...' (length: {len(response.text)})")
                generated_text = response.text
            elif not hasattr(response, 'text'):
                 logger.warning("Response object does not have a .text attribute.")


        # Get actual tokens used from response metadata
        actual_total_tokens_consumed = 0
        if response.usage_metadata:
            actual_total_tokens_consumed = response.usage_metadata.total_token_count
            # prompt_token_count_from_resp = response.usage_metadata.prompt_token_count
            # candidates_token_count_from_resp = response.usage_metadata.candidates_token_count
            logger.info(f"Gemini call for user {current_user.email} (ID: {user_db_id}) consumed {actual_total_tokens_consumed} tokens. Prompt: {response.usage_metadata.prompt_token_count}, Candidates: {response.usage_metadata.candidates_token_count}")
        else:
            # Fallback or warning if usage_metadata is not available
            # This shouldn't happen with recent Gemini versions for billable calls
            logger.warning(f"Usage metadata not available in Gemini response for user {current_user.email}. Using estimated prompt_tokens_count: {prompt_tokens_count} for debiting.")
            actual_total_tokens_consumed = prompt_tokens_count # A fallback, though not ideal

        new_total_user_tokens = current_token_usage + actual_total_tokens_consumed
        update_user_token_usage(user_db_id, new_total_user_tokens, month_start_iso)
        
        logger.info(f"Final generated text being sent for user {current_user.email} (ID: {user_db_id}): '{generated_text}'")
        return ChatResponse(response=generated_text) # Use the potentially directly extracted text
    except HTTPException as http_exc:
        raise http_exc # Re-raise specific HTTP exceptions (like 429, 401, 503)
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
    logger.info(f"Attempting PDF upload for user: {current_user.email}, filename: {file.filename}")
    logger.debug(f"GOOGLE_API_KEY available in settings: {bool(settings.GOOGLE_API_KEY)}")
    if settings.GOOGLE_API_KEY and len(settings.GOOGLE_API_KEY) > 5:
        logger.debug(f"GOOGLE_API_KEY starts with: {settings.GOOGLE_API_KEY[:5]}...")
    elif settings.GOOGLE_API_KEY:
        logger.debug("GOOGLE_API_KEY is present but very short.")
    else:
        logger.error("GOOGLE_API_KEY is not set in settings prior to API call.")


    if not settings.GOOGLE_API_KEY:
        logger.error("Critical: GOOGLE_API_KEY is not configured in settings for upload-pdf endpoint.")
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

        logger.info(f"Temporary file saved at: {file_path}. About to call genai.upload_file for {safe_filename}")
        # Upload PDF to Gemini File API
        # display_name is optional but good practice
        gemini_file = genai.upload_file(path=file_path, display_name=safe_filename)
        logger.info(f"Successfully uploaded file to Gemini. File ID: {gemini_file.name}, Display Name: {gemini_file.display_name}")
        
        # Clean up the temporary file
        os.remove(file_path)

        # The gemini_file.uri is often just the resource name like "files/your-file-id"
        # The gemini_file.name is the full resource name (e.g. "files/...")
        return UploadResponse(file_uri=gemini_file.name, display_name=gemini_file.display_name)
    except Exception as e:
        # Log the full exception for debugging
        logger.error(f"PDF upload error for user {current_user.email}, file {file.filename}: {type(e).__name__} - {str(e)}", exc_info=True)
        if os.path.exists(file_path): # Attempt cleanup if file still exists
            try:
                os.remove(file_path)
            except Exception as cleanup_e:
                logger.error(f"Error cleaning up temp file {file_path} after upload failure: {cleanup_e}")
        if "API key not valid" in str(e) or isinstance(e, genai.types.PermissionDeniedError) or "401" in str(e) or "Unauthenticated" in str(e): # Broader check for auth errors
             logger.error(f"Caught potential API key / permission error: {str(e)}")
             raise HTTPException(status_code=401, detail=f"Gemini API key is invalid or lacks permissions. Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"PDF upload error: {str(e)}")