from pydantic import BaseModel, Field


class RecognizedProduct(BaseModel):
    description: str | None = None
    supplier_product_code: str | None = None
    commercial_codes: list[str] = Field(
        default_factory=list
    )


class RecognizedInvoice(BaseModel):
    supplier_tax_id: str | None = None
    products: list[RecognizedProduct] = Field(
        default_factory=list
    )


class ProductMatchRequest(BaseModel):
    files: list[RecognizedInvoice] = Field(
        default_factory=list
    )


class SupplierProductSaveItem(BaseModel):
    supplier_id: int
    supplier_product_code: str | None = None
    product_barcode: str | None = None
    description: str
    commercial_codes: list[str] = Field(
        default_factory=list
    )
    product_id: int | None = None


class SupplierProductSaveRequest(BaseModel):
    products: list[SupplierProductSaveItem] = Field(
        default_factory=list
    )


class ImportProduct(BaseModel):
    description: str | None = None
    supplier_product_code: str | None = None

    unit_price: str
    discount_per_unit: str
    net_unit_price: str
    tax_rate: str | None = None


class ImportInvoice(BaseModel):
    type: str
    invoice_key: str
    invoice_number: str | None = None
    invoice_date: str

    supplier_tax_id: str
    currency: str = "CRC"

    products: list[ImportProduct] = Field(
        default_factory=list
    )


class InvoiceImportRequest(BaseModel):
    files: list[ImportInvoice] = Field(
        default_factory=list
    )