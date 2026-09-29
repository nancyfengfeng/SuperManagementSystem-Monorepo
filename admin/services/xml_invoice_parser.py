import xml.etree.ElementTree as ET

from decimal import Decimal


def read_xml(xml_data: bytes) -> ET.Element:
    if not xml_data:
        raise ValueError("XML file is empty")

    try:
        return ET.fromstring(xml_data)
    except ET.ParseError as exc:
        raise ValueError(
            f"Invalid XML: {exc}"
        ) from exc


def _local_name(tag: str) -> str:
    return tag.split("}", 1)[-1]


def _child(node: ET.Element | None, name: str):
    if node is None:
        return None

    for child in node:
        if _local_name(child.tag) == name:
            return child

    return None


def _children(node: ET.Element | None, name: str):
    if node is None:
        return []

    return [
        child
        for child in node
        if _local_name(child.tag) == name
    ]


def _text(node: ET.Element | None, name: str):
    child = _child(node, name)

    if child is None or child.text is None:
        return None

    return child.text.strip()


def _path_text(node: ET.Element | None, *names: str):
    current = node

    for name in names:
        current = _child(current, name)

        if current is None:
            return None

    if current.text is None:
        return None

    return current.text.strip()


def _decimal(value: str | None):
    if value is None:
        return None

    return Decimal(value)


def get_xml_type(root: ET.Element) -> str:
    tag = _local_name(root.tag)

    types = {
        "FacturaElectronica": "invoice",
        "NotaCreditoElectronica": "credit_note",
        "NotaDebitoElectronica": "debit_note",
        "MensajeHacienda": "hacienda_message",
    }

    return types.get(tag, "unknown")


def parse_invoice_products(root: ET.Element) -> list[dict]:
    detail_service = _child(
        root,
        "DetalleServicio"
    )

    if detail_service is None:
        return []

    products = []

    for line in _children(
        detail_service,
        "LineaDetalle"
    ):
        # -----------------------------
        # CodigoComercial
        # -----------------------------

        commercial_codes = []

        for code_node in _children(
            line,
            "CodigoComercial"
        ):
            code = _text(
                code_node,
                "Codigo"
            )

            if code and code not in commercial_codes:
                commercial_codes.append(code)

        supplier_product_code = (
            commercial_codes[0]
            if commercial_codes
            else None
        )

        # -----------------------------
        # Quantity
        # -----------------------------

        quantity = (
            _decimal(
                _text(
                    line,
                    "Cantidad"
                )
            )
            or Decimal("0")
        )

        # -----------------------------
        # PrecioUnitario
        # -----------------------------

        unit_price = (
            _decimal(
                _text(
                    line,
                    "PrecioUnitario"
                )
            )
            or Decimal("0")
        )

        # -----------------------------
        # Discounts
        # -----------------------------

        discount_total = Decimal("0")

        for discount in _children(
            line,
            "Descuento"
        ):
            amount = _decimal(
                _text(
                    discount,
                    "MontoDescuento"
                )
            )

            if amount is not None:
                discount_total += amount

        if quantity > 0:
            discount_per_unit = (
                discount_total / quantity
            )
        else:
            discount_per_unit = Decimal("0")

        # -----------------------------
        # Net unit price
        # -----------------------------

        subtotal = _decimal(
            _text(
                line,
                "SubTotal"
            )
        )

        if subtotal is not None and quantity > 0:
            net_unit_price = (
                subtotal / quantity
            )
        else:
            net_unit_price = (
                unit_price - discount_per_unit
            )

        # -----------------------------
        # IVA
        # -----------------------------

        tax_rate = None

        for tax in _children(
            line,
            "Impuesto"
        ):
            tax_code = _text(
                tax,
                "Codigo"
            )

            if tax_code == "01":
                rate = _decimal(
                    _text(
                        tax,
                        "Tarifa"
                    )
                )

                if rate is not None:
                    tax_rate = rate
                    break

        products.append({
            "line_number": _text(
                line,
                "NumeroLinea"
            ),

            "description": _text(
                line,
                "Detalle"
            ),

            "commercial_codes": commercial_codes,

            "supplier_product_code":
                supplier_product_code,

            "quantity": str(quantity),

            "unit_price": str(
                unit_price
            ),

            "discount_total": str(
                discount_total
            ),

            "discount_per_unit": str(
                discount_per_unit
            ),

            "net_unit_price": str(
                net_unit_price
            ),

            "tax_rate": (
                str(tax_rate)
                if tax_rate is not None
                else None
            ),
        })

    return products


def parse_invoice_info(xml_data: bytes) -> dict:
    root = read_xml(xml_data)

    document_type = get_xml_type(root)

    # Hacienda 回执不是供应商发票
    if document_type == "hacienda_message":
        return {
            "type": document_type
        }

    if document_type == "unknown":
        return {
            "type": document_type
        }

    supplier = _child(
        root,
        "Emisor"
    )

    products = parse_invoice_products(
        root
    )

    return {
        "type": document_type,

        "invoice_key": _text(
            root,
            "Clave"
        ),

        "invoice_number": _text(
            root,
            "NumeroConsecutivo"
        ),

        "invoice_date": _text(
            root,
            "FechaEmision"
        ),

        "supplier_name": _text(
            supplier,
            "Nombre"
        ),

        "supplier_tax_id": _path_text(
            supplier,
            "Identificacion",
            "Numero"
        ),

        "currency": (
            _path_text(
                root,
                "ResumenFactura",
                "CodigoTipoMoneda",
                "CodigoMoneda"
            )
            or "CRC"
        ),

        "product_count": len(
            products
        ),

        "products": products,
    }