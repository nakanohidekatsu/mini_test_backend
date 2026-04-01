from fastapi import UploadFile, HTTPException
from supabase import create_client, Client
from app.core.config import settings
import structlog
import io

logger = structlog.get_logger()


class OCRService:
    """OCR/Parserの抽象化層。差し替え可能な設計。"""

    def __init__(self, user_token: str):
        self.db: Client = create_client(settings.supabase_url, settings.supabase_service_key)
        self.db.postgrest.auth(user_token)

    async def parse(self, user_id: str, file: UploadFile, source_type: str, source_name: str) -> dict:
        content = await file.read()
        raw_text = await self._extract_text(content, source_type, file.filename or "")

        result = self.db.from_("question_sources").insert({
            "user_id": user_id,
            "source_type": source_type,
            "source_name": source_name,
            "raw_text": raw_text,
        }).execute()

        return {"source_id": result.data[0]["id"], "raw_text": raw_text[:500]}

    async def _extract_text(self, content: bytes, source_type: str, filename: str) -> str:
        if source_type == "text":
            return content.decode("utf-8", errors="replace")
        elif source_type == "pdf":
            return await self._extract_pdf(content)
        elif source_type == "image":
            return await self._extract_image(content)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported source_type: {source_type}")

    async def _extract_pdf(self, content: bytes) -> str:
        # 1st: pymupdf でテキスト抽出（最も信頼性が高い）
        try:
            import fitz  # pymupdf
            doc = fitz.open(stream=content, filetype="pdf")
            text = "\n".join(page.get_text() for page in doc).strip()
            doc.close()
            if len(text) >= 20:
                return text
        except Exception as e:
            logger.warning("fitz_text_extraction_failed", error=str(e))

        # 2nd: PyPDF2 でフォールバック
        try:
            import PyPDF2
            reader = PyPDF2.PdfReader(io.BytesIO(content))
            text = "\n".join(page.extract_text() or "" for page in reader.pages).strip()
            if len(text) >= 20:
                return text
        except Exception as e:
            logger.warning("pypdf2_extraction_failed", error=str(e))

        # 3rd: OCR（tesseract が利用可能な環境のみ）
        try:
            import fitz
            import pytesseract
            from PIL import Image

            doc = fitz.open(stream=content, filetype="pdf")
            pages_text = []
            for page in doc:
                mat = fitz.Matrix(2, 2)
                pix = page.get_pixmap(matrix=mat)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                pages_text.append(pytesseract.image_to_string(img, lang="jpn+eng"))
            doc.close()
            text = "\n".join(pages_text).strip()
            if text:
                return text
        except Exception as e:
            logger.warning("pdf_ocr_failed", error=str(e))

        raise HTTPException(status_code=422, detail="PDFからテキストを抽出できませんでした。テキスト形式のPDFをお試しください。")

    async def _extract_image(self, content: bytes) -> str:
        try:
            import pytesseract
            from PIL import Image
            img = Image.open(io.BytesIO(content))
            return pytesseract.image_to_string(img, lang="jpn+eng")
        except Exception as e:
            logger.error("ocr_extraction_failed", error=str(e))
            raise HTTPException(status_code=422, detail="OCR処理に失敗しました")
