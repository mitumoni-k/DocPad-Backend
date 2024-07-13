from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import tempfile
import os
import shutil
from server.api.functions import (extract_from_docx, extract_from_pdf, generate_summary_pdf)

app = FastAPI(title="DocPad API documentation")

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
            # Copy the contents of the uploaded file to the temporary file
            shutil.copyfileobj(file.file, temp_file)
            temp_file_path = temp_file.name

        # Process the file based on its extension
        if temp_file_path.endswith('.pdf'):
            highlighted_texts_with_headings = extract_from_pdf(temp_file_path)
        elif temp_file_path.endswith('.docx'):
            highlighted_texts_with_headings = extract_from_docx(temp_file_path)
        else:
            os.unlink(temp_file_path)  # Delete the temporary file
            return JSONResponse(content={
                "error": "Unsupported File Format"
            }, status_code=400)

        # Generate the summary PDF
        summary_path = generate_summary_pdf(highlighted_texts_with_headings, "summary.pdf")

        # Return the generated PDF
        return FileResponse(summary_path, media_type="application/pdf", filename="summary.pdf")

    except Exception as e:
        # Handle any exceptions
        return JSONResponse(content={
            "error": f"An error occurred: {str(e)}"
        }, status_code=500)

    finally:
        # Ensure the temporary file is deleted
        if 'temp_file_path' in locals():
            try:
                os.unlink(temp_file_path)
            except Exception:
                pass  # If deletion fails, we don't want to raise an error here
