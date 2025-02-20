import boto3
import sys
from collections import defaultdict


def get_kv_map(file_name):
    # Read the PDF file as bytes
    with open(file_name, 'rb') as file:
        document_bytes = file.read()
    print("Document loaded:", file_name)

    # Initialize a boto3 client
    client = boto3.Session(aws_access_key_id="",
                          aws_secret_access_key="",
                          region_name='eu-central-1').client('textract')

    # Call analyze_document API; per AWS docs, PDFs are supported here if within limits
    response = client.analyze_document(
        Document={'Bytes': document_bytes},
        FeatureTypes=['FORMS']
    )

    blocks = response['Blocks']
    key_map = {}
    value_map = {}
    block_map = {}

    for block in blocks:
        block_id = block['Id']
        block_map[block_id] = block
        if block['BlockType'] == "KEY_VALUE_SET":
            # Distinguish keys from values based on the 'EntityTypes' field
            if 'KEY' in block.get('EntityTypes', []):
                key_map[block_id] = block
            else:
                value_map[block_id] = block

    return key_map, value_map, block_map


def get_text(block, block_map):
    """Extracts text from a block by concatenating text from its child relationships."""
    text = ""
    if block and 'Relationships' in block:
        for relationship in block['Relationships']:
            if relationship['Type'] == 'CHILD':
                for child_id in relationship['Ids']:
                    child = block_map.get(child_id)
                    if child and child['BlockType'] == 'WORD':
                        text += child['Text'] + ' '
                    elif child and child['BlockType'] == 'SELECTION_ELEMENT' and child.get(
                            'SelectionStatus') == 'SELECTED':
                        text += 'X '  # Marking selected checkboxes
    return text.strip()


def find_value_block(key_block, value_map):
    """Finds the value block associated with a given key block."""
    if 'Relationships' in key_block:
        for relationship in key_block['Relationships']:
            if relationship['Type'] == 'VALUE':
                for value_id in relationship['Ids']:
                    return value_map.get(value_id)
    return None


def get_kv_relationship(key_map, value_map, block_map):
    """Builds the key–value pairs from the key and value maps."""
    kvs = defaultdict(list)
    for key_id, key_block in key_map.items():
        key_text = get_text(key_block, block_map)
        value_block = find_value_block(key_block, value_map)
        value_text = get_text(value_block, block_map) if value_block else ""
        kvs[key_text].append(value_text)
    return kvs


def print_kv_pairs(kvs):
    """Prints the key–value pairs to the console."""
    for key, values in kvs.items():
        print(f"{key}: {', '.join(values)}")


def main(file_name):
    key_map, value_map, block_map = get_kv_map(file_name)
    kvs = get_kv_relationship(key_map, value_map, block_map)
    print("\nExtracted Key–Value Pairs:\n")
    print_kv_pairs(kvs)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python script.py <PDF file>")
        sys.exit(1)
    main(sys.argv[1])
