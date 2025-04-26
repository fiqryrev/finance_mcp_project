"""
Prompts for processing multitype invoices using LLMs
"""

class PromptMultitypeInvoices:
    """
    Collection of prompts for processing different types of invoices
    using language models.
    """
    
    PROMPT_BASE_CLASSIFY_MULTITYPE_INVOICES = """
    You are an intelligent OCR (optical character recognition) assistant.
    Analyze the provided document and classify its type.
    The document might be in Bahasa Indonesia, English, or other languages.
    
    Return the document type in the following JSON format:
    {
        "document_type": "<document_type>",
        "confidence": "<confidence_level>",
        "details": "<additional_details_about_classification>"
    }
    
    Where <document_type> is one of the following:
    - "invoice" (customer invoice, or receipt about the transaction proof)
    - "other" (if the document doesn't fit any of the above categories)
    
    <confidence_level> should be a value between 0.0 and 1.0 indicating your confidence in the classification.
    <additional_details> should include any specific fields or markers that informed your classification.
    """
    
    PROMPT_BASE_PROCESS_MULTITYPE_INVOICES = """
    You are an intelligent OCR (optical character recognition).
    Please perform OCR analysis on the provided images or documents. 
    The images/documents may contain text in Bahasa Indonesia, English, or other languages. 
    Use sequence structure context, translation and general knowledge to assist in this task.
    Your objectives are as follows:
    1. Date Formatting: Use the Indonesian date format, which is "dd/mm/yyyy"
    2. Numeric Formatting: Use the International Numbering System format where a comma (,) is used as a thousand separator and a period (.) is used as a decimal separator. For example, the correct format for four million would be "4,000,000.00".
    3. Empty Fields: Use empty string ("") for filling in missing fields.
    4. Document Type: Use lowercase letters for document type.
    Return the result in the specified JSON format:
    """
    
    PROMPT_OUTPUT_INVOICE = """
    {
        'document_type': 'invoice',
        'customer_address': '<customer_address>',
        'customer_email': '<customer_email>',
        'customer_name': '<customer_name>',
        'customer_phone': '<customer_phone>',
        'delivery_fee_amount': '<delivery_fee_amount>',
        "fully_paid_amount": "<total_amount_paid_by_the_user>. Fully settling the invoice. This may be referred to as 'Lunas' or other similar terms indicating complete payment.",
        'down_payment_amount': "<down_payment_amount>.",
        'discount_amount': '<discount_amount>. Extract the total discount amount, focusing on terms like "diskon", "potongan harga", "korting", "rabatt". Ensure this value reflects a reduction in the total price, not related to taxes.',
        'grand_total': '<grand_total>. This should represent the absolute final amount due, including any additional charges (e.g., delivery fees), taxes, and any discounts applied after total_amount is calculated. Look for related terms like "netto", "neto", "jumlah yang dibayarkan", "total keseluruhan", or other phrases indicating the final amount payable by the customer after all adjustments have been made.',
        'invoice_date': '<invoice_date DD-MM-YYYY format>. Extract the actual invoice date from the document. Look for terms or labels like "tanggal invoice", "invoice date", "inv.date", "tanggal faktur", or other similar variations. It might not always be at the top of the document; look for it throughout, including areas near **signatures**, **stamps**, or **meterai** (official seals), often found at the **bottom** or **corners** of the document. If multiple dates are present, prioritize the one closest to a signature, stamp, or labeled as "Tanggal" or "Date".',
        'invoice_due_date': '<invoice_due_date DD-MM-YYYY format>. It may be in the form of "Tanggal jatuh tempo" or other similar terms.',
        'invoice_number': '<invoice_number>. Extract the invoice number, which can be alphanumeric, and may include letters, numbers, and special characters (such as dot ".", hyphens "-", slashes "/", or underscores "_"). The invoice number is often labeled with terms like "Invoice Number", "Nomor Faktur", "No. Invoice", "IN-Pxxx", or similar. Ensure that the extracted value corresponds to the unique identifier of the invoice and avoid extracting unrelated numeric or alphanumeric sequences.',
        'items': [{'item_code': '<item_code>. Extract the item code **only** if it appears in a dedicated column or section explicitly labeled as "Kode", "SKU", "item code", "kode barang", "product code", or other similar terms. Do **not** extract item codes from within the "item_product_name" or based on patterns found in the product name itself. If no dedicated column or label is present, set "item_code" to null. Avoid making assumptions or predictions about item codes embedded in "item_product_name" or "item_description".',
                    'item_product_name': '<product_name>. This field contains the name of the product/service/artikel, which is generally a descriptive text. Include measurement sizes (e.g., weight, dimensions, volume, etc), or additional specifications if they are part of the printed product name that are part of the product name or appear immediately adjacent to it (in the middle or at the end). For example, "CORNICE ADHESIVE @20KG", "CASTING APLUS STANDARD @ 18KG", "IMPRA WS-162 B SHP BROWN-1L", "CATUR SILICA BOARD 4MM X 1220MM X 2440MM", "Wireless Headphones", "Laptop Stand", "Product X 500ml". Ensure to capture the full product name with sizes and specifications integrated. Do not separate the size and additional specifications from the name if it is listed in the middle or at the end of the document.',
                    'item_description': '<description_product>. Extract the product description if it appears in a dedicated column or section labeled with terms like "warna" (color), "item description", "deskripsi", or other similar terms. Provide a detailed description of the product, if available. If size or measurement specifications are not adjacent to the product name but exist elsewhere in the document, include them here. Use this field to capture additional product details, specifications, or features that aren not part of the item_product_name or item_code. Descriptions may include information like size, color/warna, material, model, function, or other specific attributes of the product. It may also mention how the product is used or additional details that would help a customer understand the product better.',
                    'item_discount_amount': '<item_discount_amount or potongan_harga>. It may be in the form of Bahasa Indonesia terms, such as potongan harga, diskon, korting, rabat, potongan, pengurangan harga, etc. Convert to comma (,) as thousand separator and period (.) as decimal point',
                    'item_discount_percentage': '<item_discount_percentage>. This is for single/one-level discount percentages only.',
                    "item_discount_string": "<multilevel_discount_percentage>. For multi-level discounts, It always containns or separate each level with '+' sign. Only include items with bi-level or higher discounts. For example: '15.00+3.00+5.00' for a three-level discount of 15%, 3%, and 5%. And '10.00+5.00' or '10+5' for a bi-level discount of '10%' and '5%'. If there's no discount, or only a single level discount, ignore the entry.",
                    'item_price_unit': '<item_price_per_unit>. The price of each unit of the item.',
                    'item_quantity': '<item_quantity>.',
                    'item_tax_amount': '<item_tax_amount>.',
                    'item_tax_pct': '<item_tax_percentage>',
                    'item_total_amount': '<item_total_amount>.',
                    'item_unit': '<item_unit>',
                    'currency': '<currency_in_ISO_4217>. Always convert currency into ISO 4217 Format. For example: "Rp" to "IDR", "$" to "USD", etc. If not specified return IDR'}],
        'purchase_order_number': '<purchase_order_number>',
        'subtotal_amount': '<subtotal_amount>.',
        'supplier_account_name': '<supplier_account_holder_name>. In a bank account, this is the name of the account holder.',
        'supplier_address': '<supplier_address>',
        'supplier_bank': '<supplier_bank>',
        'supplier_bank_account': '<supplier_bank_account>',
        'supplier_email': '<supplier_email>',
        'supplier_company_name': '<supplier_name>. Company name, oftenly started with pt, ud, cv, firma, etc or containing llc, pvt, ltd, etc. It is not buyer, client, or customer.',
        'supplier_brand_name':'<supplier_brand_name>. Name on logo or trademark image. Different from company name.',
        'supplier_npwp': '<supplier_npwp>',
        'supplier_phone': '<supplier_phone>',
        'tax_amount': '<tax_amount>. Extract the tax amount, focusing on terms like "pajak", "PPN", "PPh", "tax". Ensure this value is separate from any discounts.',
        'tax_inclusive_amount': '<tax_inclusive_amount>.',
        'total_amount': '<total_amount>. This is the sum of the subtotal_amount plus taxes before additional charges (like delivery fees) or discounts are applied.'
    }
    """
    
    PROMPT_OUTPUT_OTHER = """
    {
        'document_type': 'other',
        'content_summary': '<summary_of_document_content>',
        'detected_fields': {
            'dates': ['<list_of_dates_found>'],
            'amounts': ['<list_of_monetary_amounts_found>'],
            'company_names': ['<list_of_company_names_found>'],
            'person_names': ['<list_of_person_names_found>']
        },
        'document_category': '<best_guess_category>',
        'language': '<detected_language>'
    }
    """