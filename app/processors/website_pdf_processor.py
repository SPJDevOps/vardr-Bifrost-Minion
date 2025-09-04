import os
from urllib.parse import urlparse
from pyppeteer import launch
from app.processors.base_processor import BaseProcessor
from app.models.exceptions import DependencyNotFoundError, InternalError


class WebsitePdfProcessor(BaseProcessor):
    def __init__(self, broker, status_queue):
        super().__init__(broker, status_queue, "/tmp/website-pdfs/")

    async def _download_dependency(self, download):
        """Convert website to PDF using pyppeteer"""
        url = download.dependency
        sanitized_name = self.sanitize_filename(url)
        pdf_path = os.path.join(self.temp_dir, f"{sanitized_name}.pdf")

        print(f"Converting website {url} to PDF...")

        try:
            # Launch browser with longer timeout for page loads
            browser = await launch({
                'args': ['--no-sandbox', '--disable-setuid-sandbox'],
                'timeout': 60000  # 1 minute timeout for browser launch
            })
            page = await browser.newPage()
            
            # Set longer timeout for page navigation
            await page.goto(url, {
                'waitUntil': 'networkidle0',
                'timeout': 120000  # 2 minute timeout for page load
            })
            
            await page.pdf({
                'path': pdf_path, 
                'format': 'A4',
                'timeout': 60000  # 1 minute timeout for PDF generation
            })
            await browser.close()
            
            print(f"Website {url} converted to PDF successfully.")
            download.file_path = pdf_path
            
        except Exception as e:
            if "net::ERR_NAME_NOT_RESOLVED" in str(e) or "net::ERR_CONNECTION_REFUSED" in str(e):
                raise DependencyNotFoundError(f"Website not accessible: {url}")
            else:
                raise InternalError(f"Error converting website to PDF: {str(e)}") 