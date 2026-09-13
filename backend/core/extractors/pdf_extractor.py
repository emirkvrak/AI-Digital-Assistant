import fitz
from core.extractors.base_extractor import BaseExtractor

class PDFExtractor(BaseExtractor):
    def extract_text(self) -> str:
        try:
            self.file_stream.seek(0)
            full_text = ""

            with fitz.open(stream=self.file_stream.read(), filetype="pdf") as doc:
                for page in doc:
                    page_text = page.get_text("text")
                    full_text += page_text.strip() + " "

            return " ".join(full_text.split()).strip()
        except Exception as e:
            print(f"❌ PDF metni çıkarma hatası: {e}")
            return ""
