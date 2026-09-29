from pydantic import BaseModel

class SupplierCreate(BaseModel):
    name: str

class SupplierLink(BaseModel):
    legal_name: str
    tax_id: str