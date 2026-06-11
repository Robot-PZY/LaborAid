"""Test export functions directly with database data."""
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import text
from app.core.database import AsyncSessionLocal
from app.models.document import Document
from app.services.docgen.word_export import export_to_docx
from app.services.docgen.pdf_export import export_to_pdf
from app.services.docgen.html_export import export_to_html

async def test_exports():
    async with AsyncSessionLocal() as session:
        # Get first document with content
        result = await session.execute(text(
            "SELECT id, title, content FROM documents WHERE content IS NOT NULL AND LENGTH(content) > 0 LIMIT 1"
        ))
        row = result.fetchone()
        
        if not row:
            print("No documents with content found")
            return
        
        doc_id, title, content = row
        print(f"Testing export for doc {doc_id}: {title}")
        print(f"Content length: {len(content)} chars")
        
        # Create a mock Document object
        doc = Document()
        doc.id = doc_id
        doc.title = title
        doc.content = content
        
        output_dir = Path("test_exports")
        output_dir.mkdir(exist_ok=True)
        
        # Test HTML export
        print("\n=== Testing HTML export ===")
        try:
            html_path = await export_to_html(doc, output_dir)
            print(f"[OK] HTML export: {html_path}")
        except Exception as e:
            print(f"[FAIL] HTML export: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
        
        # Test Word export
        print("\n=== Testing Word export ===")
        try:
            docx_path = await export_to_docx(doc, output_dir)
            print(f"[OK] Word export: {docx_path}")
        except Exception as e:
            print(f"[FAIL] Word export: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
        
        # Test PDF export
        print("\n=== Testing PDF export ===")
        try:
            pdf_path = await export_to_pdf(doc, output_dir)
            print(f"[OK] PDF export: {pdf_path}")
        except Exception as e:
            print(f"[FAIL] PDF export: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()

asyncio.run(test_exports())
