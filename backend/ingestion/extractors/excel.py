import pandas as pd
from typing import List
from models.schemas import RawLineItem, ExtractedField, SourceRef

def extract_from_excel(file_path: str) -> List[RawLineItem]:
    df = pd.read_excel(file_path)
    # Simple heuristic extraction for MVP
    # Map common column names to our expected fields
    col_mapping = {}
    for col in df.columns:
        col_lower = str(col).lower()
        if "mark" in col_lower or "type" in col_lower:
            col_mapping["mark"] = col
        elif "qty" in col_lower or "quantity" in col_lower:
            col_mapping["quantity"] = col
        elif "desc" in col_lower:
            col_mapping["description"] = col
        elif "sku" in col_lower or "part" in col_lower or "model" in col_lower:
            col_mapping["specified_sku"] = col
            
    items = []
    for idx, row in df.iterrows():
        # Treat NaN as None
        row_dict = row.where(pd.notnull(row), None).to_dict()
        
        item = RawLineItem(raw_data=row_dict)
        
        if "mark" in col_mapping and row_dict.get(col_mapping["mark"]):
            item.mark = ExtractedField(value=str(row_dict[col_mapping["mark"]]), source_ref=SourceRef(cell=f"{col_mapping['mark']}{idx+2}"))
            
        if "quantity" in col_mapping and row_dict.get(col_mapping["quantity"]):
            try:
                qty = int(row_dict[col_mapping["quantity"]])
                item.quantity = ExtractedField(value=qty, source_ref=SourceRef(cell=f"{col_mapping['quantity']}{idx+2}"))
            except ValueError:
                pass
                
        if "description" in col_mapping and row_dict.get(col_mapping["description"]):
            item.description = ExtractedField(value=str(row_dict[col_mapping["description"]]), source_ref=SourceRef(cell=f"{col_mapping['description']}{idx+2}"))
            
        if "specified_sku" in col_mapping and row_dict.get(col_mapping["specified_sku"]):
            item.specified_sku = ExtractedField(value=str(row_dict[col_mapping["specified_sku"]]), source_ref=SourceRef(cell=f"{col_mapping['specified_sku']}{idx+2}"))
            
        items.append(item)
        
    return items
