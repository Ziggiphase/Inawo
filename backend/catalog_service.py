import pandas as pd
import pdfplumber
import io
from sqlalchemy.orm import Session
from models import Product

async def process_catalog_file(file_bytes: bytes, filename: str, business_id: int, db: Session):
    """
    Standard Software Engineering Practice: 
    A dedicated service layer for Data Ingestion.
    Extracts structured product data from Excel/CSV/PDF and populates the database.
    """
    extracted_items = []

    try:
        # 1. Handle Excel / CSV Files
        if filename.endswith(('.xlsx', '.xls', '.csv')):
            if filename.endswith('.csv'):
                df = pd.read_csv(io.BytesIO(file_bytes))
            else:
                df = pd.read_excel(io.BytesIO(file_bytes))
            
            # Standardize columns to lowercase to find 'name', 'price', 'description'
            df.columns = [str(c).lower().strip() for c in df.columns]
            
            for _, row in df.iterrows():
                # Flexible column matching
                name = row.get('name') or row.get('item') or row.get('product')
                price_val = row.get('price') or row.get('cost') or row.get('amount')
                desc = row.get('description') or row.get('details') or ""
                
                if name:
                    try:
                        clean_price = float(str(price_val).replace(',', '').replace('₦', '').strip())
                    except:
                        clean_price = 0.0

                    extracted_items.append({
                        "name": str(name),
                        "price": clean_price,
                        "description": str(desc)
                    })

        # 2. Handle PDF Files
        elif filename.endswith('.pdf'):
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        # For PDF, we might need a LLM extraction pass in the future, 
                        # but for now we store it as a generic product entry or split by line
                        lines = text.split('\n')
                        for line in lines:
                            if len(line) > 5 and '₦' in line: # Basic heuristic for a price line
                                extracted_items.append({
                                    "name": line,
                                    "price": 0.0, # Requires more complex regex
                                    "description": "Extracted from PDF"
                                })

        # 3. Bulk Insert into Database
        if extracted_items:
            # Clear old catalog first (optional, but good for updates)
            db.query(Product).filter(Product.business_id == business_id).delete()
            
            new_products = [
                Product(
                    business_id=business_id,
                    name=item['name'],
                    price=item['price'],
                    description=item['description']
                ) for item in extracted_items
            ]
            db.add_all(new_products)
            db.commit()
            
            return {"status": "success", "items_processed": len(new_products)}
        else:
            return {"status": "warning", "message": "No valid products found in file."}

    except Exception as e:
        db.rollback()
        print(f"❌ Catalog Processing Error: {str(e)}")
        raise e
