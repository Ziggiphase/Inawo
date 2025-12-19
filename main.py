# Replace your existing extract_text_from_file with this:

def extract_text_from_file(file_content: bytes, filename: str) -> str:
    try:
        stream = BytesIO(file_content)
        
        if filename.endswith('.csv'):
            df = pd.read_csv(stream)
            return df.to_string()
        
        elif filename.endswith(('.xls', '.xlsx')):
            df = pd.read_excel(stream)
            return df.to_string()
        
        elif filename.endswith('.pdf'):
            text_output = []
            with pdfplumber.open(stream) as pdf:
                for page in pdf.pages:
                    # Try extracting tables first
                    tables = page.extract_tables()
                    if tables:
                        for table in tables:
                            for row in table:
                                # Clean row and join with pipes for AI readability
                                clean_row = " | ".join([str(i).strip() for i in row if i])
                                text_output.append(clean_row)
                    
                    # Also get the regular text
                    page_text = page.extract_text()
                    if page_text:
                        text_output.append(page_text)
            return "\n".join(text_output)
        
        elif filename.endswith(('.doc', '.docx')):
            doc = docx.Document(stream)
            return "\n".join([para.text for para in doc.paragraphs])
            
    except Exception as e:
        print(f"Error parsing {filename}: {e}")
        return f"[Error: Could not read content from {filename}]"
    
    return ""
