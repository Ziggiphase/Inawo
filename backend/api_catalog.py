from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Business
from dependencies import get_current_business
from catalog_service import process_catalog_file

router = APIRouter(prefix="/api/catalog", tags=["Catalog Ingestion"])

@router.post("/upload")
async def upload_catalog(
    file: UploadFile = File(...),
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db)
):
    """
    Endpoint for businesses to upload their price lists or catalogs.
    Accepts .pdf, .csv, .xls, and .xlsx files.
    """
    allowed_extensions = ('.pdf', '.csv', '.xls', '.xlsx')
    if not file.filename.lower().endswith(allowed_extensions):
        raise HTTPException(
            status_code=400, 
            detail="Invalid file format. Only PDF, CSV, and Excel files are supported."
        )

    try:
        # Read file into memory
        file_bytes = await file.read()
        
        # Process the file using our dedicated service layer
        result = await process_catalog_file(
            file_bytes=file_bytes, 
            filename=file.filename, 
            business_id=current_business.id, 
            db=db
        )
        
        # Update the business's raw knowledge base text as a fallback
        # In a real app, you might also extract full text for RAG alongside structured products
        current_business.knowledge_base_text = f"Catalog uploaded: {file.filename}. Check Products database for items."
        db.commit()

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process file: {str(e)}")
