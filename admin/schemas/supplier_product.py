from pydantic import BaseModel

class BarcodeUpdate(BaseModel):
    barcode: str