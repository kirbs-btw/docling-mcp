"""Tools for manipulating Docling documents."""

from docling_core.types.doc.document import (
    DocItem,
    GroupItem,
    RefItem,
    SectionHeaderItem,
    TextItem,
    TitleItem,
)

from docling_mcp.logger import setup_logger
from docling_mcp.shared import local_document_cache, mcp
import json
import re

# Create a default project logger
logger = setup_logger()


@mcp.tool()
def get_overview_of_document_anchors(document_key: str) -> str:
    """Retrieves a structured overview of a document from the local document cache.

    This tool returns a text representation of the document's structure, showing
    the hierarchy and types of elements within the document. Each line in the
    output includes the document anchor reference and item label.

    Args:
        document_key (str): The unique identifier for the document in the local cache.

    Returns:
        str: A string containing the hierarchical structure of the document with
             indentation to show nesting levels, along with anchor references.

    Raises:
        ValueError: If the specified document_key does not exist in the local cache.

    Example:
        get_overview_of_document_anchors(document_key="doc123")
    """
    if document_key not in local_document_cache:
        doc_keys = ", ".join(local_document_cache.keys())
        raise ValueError(
            f"document-key: {document_key} is not found. Existing document-keys are: {doc_keys}"
        )

    doc = local_document_cache[document_key]

    lines = []
    slevel = 0
    for item, level in doc.iterate_items():
        ref = item.get_ref()

        if isinstance(item, DocItem):
            if isinstance(item, TitleItem):
                lines.append(f"[anchor:{ref.cref}] {item.label}: {item.text}")

            elif isinstance(item, SectionHeaderItem):
                slevel = item.level
                indent = "  " * (level + slevel)
                lines.append(
                    f"{indent}[anchor:{ref.cref}] {item.label}-{level}: {item.text}"
                )

            else:
                indent = "  " * (level + slevel + 1)
                lines.append(f"{indent}[anchor:{ref.cref}] {item.label}")

        elif isinstance(item, GroupItem):
            indent = "  " * (level + slevel + 1)
            lines.append(f"{indent}[anchor:{ref.cref}] {item.label}")

    return "\n".join(lines)


@mcp.tool()
def get_text_of_document_item_at_anchor(document_key: str, document_anchor: str) -> str:
    """Retrieves the text content of a specific document item identified by its anchor.

    This tool extracts the text from a document item at the specified anchor location
    within a document that exists in the local document cache.

    Args:
        document_key (str): The unique identifier for the document in the local cache.
        document_anchor (str): The anchor reference that identifies the specific item
                               within the document.

    Returns:
        str: A formatted string containing the text content of the specified item,
             wrapped in code block formatting.

    Raises:
        ValueError: If the specified document_key does not exist in the local cache.
        ValueError: If the item at the specified anchor is not a textual item.

    Example:
        get_text_of_document_item_at_anchor(document_key="doc123", document_anchor="#/texts/2")
    """
    if document_key not in local_document_cache:
        doc_keys = ", ".join(local_document_cache.keys())
        raise ValueError(
            f"document-key: {document_key} is not found. Existing document-keys are: {doc_keys}"
        )

    doc = local_document_cache[document_key]

    ref = RefItem(cref=document_anchor)
    item = ref.resolve(doc=doc)

    if isinstance(item, TextItem):
        text = item.text
    else:
        raise ValueError(
            f"Item at {document_anchor} for document-key: {document_key} is not a textual item."
        )

    return f"The text of {document_anchor} for document-key with {document_key} is:\n\n```{text}```\n\n"


@mcp.tool()
def update_text_of_document_item_at_anchor(
    document_key: str, document_anchor: str, updated_text: str
) -> str:
    """Updates the text content of a specific document item identified by its anchor.

    This tool modifies the text of an existing document item at the specified anchor
    location within a document that exists in the local document cache.

    Args:
        document_key (str): The unique identifier for the document in the local cache.
        document_anchor (str): The anchor reference that identifies the specific item
                               within the document.
        updated_text (str): The new text content to replace the existing content.

    Returns:
        str: A confirmation message indicating the text was successfully updated.

    Raises:
        ValueError: If the specified document_key does not exist in the local cache.
        ValueError: If the item at the specified anchor is not a textual item.

    Example:
        update_text_of_document_item_at_anchor(document_key="doc123", document_anchor="#/texts/2", updated_text="This is the new content.")
    """
    if document_key not in local_document_cache:
        doc_keys = ", ".join(local_document_cache.keys())
        raise ValueError(
            f"document-key: {document_key} is not found. Existing document-keys are: {doc_keys}"
        )

    doc = local_document_cache[document_key]

    ref = RefItem(cref=document_anchor)
    item = ref.resolve(doc=doc)

    if isinstance(item, TextItem):
        item.text = updated_text
    else:
        raise ValueError(
            f"Item at {document_anchor} for document-key: {document_key} is not a textual item."
        )

    return f"Updated the text at {document_anchor} for document with key {document_key}"


@mcp.tool()
def delete_document_items_at_anchors(
    document_key: str, document_anchors: list[str]
) -> str:
    """Deletes multiple document items identified by their anchors.

    This tool removes specified items from a document that exists in the local
    document cache, based on their anchor references.

    Args:
        document_key (str): The unique identifier for the document in the local cache.
        document_anchors (list[str]): A list of anchor references identifying the items
                                      to be deleted from the document.

    Returns:
        str: A confirmation message indicating the items were successfully deleted.

    Raises:
        ValueError: If the specified document_key does not exist in the local cache.

    Example:
        delete_document_items_at_anchors(document_key="doc123", document_anchors=["#/texts/2", "#/tables/1"])
    """
    if document_key not in local_document_cache:
        doc_keys = ", ".join(local_document_cache.keys())
        raise ValueError(
            f"document-key: {document_key} is not found. Existing document-keys are: {doc_keys}"
        )

    doc = local_document_cache[document_key]

    items = []
    for _ in document_anchors:
        ref = RefItem(cref=_)
        items.append(ref.resolve(doc=doc))

    doc.delete_items(node_items=items)

    return f"Deleted the {document_anchors} for document with key {document_key}"


@mcp.tool
def output_optimization(llm_output: str, schema: str) -> dict:
    prediction = llm_output.replace(r"\_", "_")  
    
    prediction = fix_invalid_json(prediction)
    
    prediction_dict = json.loads(prediction)
    
    prediction_dict = validate_data_against_schema(prediction_dict, schema)
    
    return prediction_dict

@mcp.tool    
def fix_invalid_json(json_text):
    # Regex pattern to find cases where a key is followed by an object containing only a string
    pattern = r'("\w+":)\s*\{\s*"([^"]+)"\s*\}'

    # Replace the invalid JSON structure with a proper key-value pair
    fixed_json_text = re.sub(pattern, r'\1 "\2"', json_text)
    return fixed_json_text

@mcp.tool
def validate_data_against_schema(data: dict, schema: dict) -> dict:
    """
    Recursively validates and sanitizes data from an LLM so that it fits the specified schema.

    For each key in the schema:
      - If the key is missing in data, it is added with an empty version built from the schema.
      - If the key is present:
          * If the expected value (from schema) is a dict, the function validates the sub-dictionary recursively.
          * Otherwise, it ensures the value is either a string or a list of strings.
            If not, it falls back to the default value from the schema.

    Extra keys in data that are not in the schema are removed.
    """
    validated = {}
    for key, expected in schema.items():
        if key not in data:
            # Key is missing; create an empty version based on the expected schema
            validated[key] = _make_empty_value(expected)
        else:
            candidate = data[key]
            # If the schema expects a dict, handle recursively
            if isinstance(expected, dict):
                if isinstance(candidate, dict):
                    validated[key] = validate_data_against_schema(candidate, expected)
                else:
                    validated[key] = _make_empty_value(expected)
            else:
                # For non-dict values, ensure candidate is a string or list of strings
                if _is_valid_value_type(candidate):
                    validated[key] = candidate
                else:
                    validated[key] = expected
    return validated

@mcp.tool
def _make_empty_value(default):
    """
    Creates an "empty" version of the default value from the schema.
    If the default is a dict, it recursively builds an empty dict with the same structure.
    Otherwise, it returns the default (which can be an empty string or list, etc.).
    """
    if isinstance(default, dict):
        return {k: _make_empty_value(v) for k, v in default.items()}
    return default

@mcp.tool
def _is_valid_value_type(value):
    """
    Checks whether the value is either a string or a list of strings.
    """
    if isinstance(value, str):
        return True
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return True
    return False