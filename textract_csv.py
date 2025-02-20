import os
import sys
import json
import boto3
from io import BytesIO
from pprint import pprint


def get_text(result, blocks_map):
    """Extracts text from a block by combining its child words and selection elements."""
    text = ''
    if 'Relationships' in result:
        for relationship in result['Relationships']:
            if relationship['Type'] == 'CHILD':
                for child_id in relationship['Ids']:
                    word = blocks_map.get(child_id)
                    if word and word['BlockType'] == 'WORD':
                        # If the word contains a comma and is numeric when commas are removed, wrap it in quotes
                        if "," in word['Text'] and word['Text'].replace(",", "").isnumeric():
                            text += f'"{word["Text"]}" '
                        else:
                            text += word['Text'] + ' '
                    elif word and word['BlockType'] == 'SELECTION_ELEMENT':
                        if word.get('SelectionStatus') == 'SELECTED':
                            text += 'X '
    return text.strip()


def get_rows_columns_map(table_result, blocks_map):
    """
    Creates a mapping of rows and columns for a table block.
    Returns a dictionary of rows with their corresponding cells' text and a list of confidence scores.
    """
    rows = {}
    scores = []
    for relationship in table_result.get('Relationships', []):
        if relationship['Type'] == 'CHILD':
            for child_id in relationship['Ids']:
                cell = blocks_map.get(child_id)
                if cell and cell['BlockType'] == 'CELL':
                    row_index = cell['RowIndex']
                    col_index = cell['ColumnIndex']
                    if row_index not in rows:
                        rows[row_index] = {}
                    scores.append(str(cell.get('Confidence', 0)))
                    rows[row_index][col_index] = get_text(cell, blocks_map)
    return rows, scores


def generate_table_csv(table_result, blocks_map, table_index):
    """
    Generates a CSV string for the table block.
    """
    rows, scores = get_rows_columns_map(table_result, blocks_map)
    table_id = f'Table_{table_index}'
    csv_output = f'Table: {table_id}\n\n'

    # Create CSV rows
    for row_index in sorted(rows.keys()):
        row_data = rows[row_index]
        # Sort columns by their index
        row_text = ",".join(row_data[col_index] for col_index in sorted(row_data.keys()))
        csv_output += row_text + "\n"

    # Append confidence scores at the end
    csv_output += "\nConfidence Scores (per cell):\n"
    # Assuming each row has same number of columns, get the number of columns from the first row
    if rows:
        col_count = len(next(iter(rows.values())))
        for i, score in enumerate(scores, start=1):
            csv_output += score + ","
            if i % col_count == 0:
                csv_output += "\n"
    csv_output += "\n\n"
    return csv_output


def get_table_csv_results(file_name):
    """
    Reads a PDF file, sends it to Textract to extract tables,
    and returns a CSV string with the extracted table data.
    """
    # Read PDF file bytes
    with open(file_name, 'rb') as file:
        pdf_bytes = file.read()
    print('PDF loaded:', file_name)

    # Initialize a boto3 client
    client = boto3.Session(aws_access_key_id="",
                           aws_secret_access_key="",
                           region_name='eu-central-1').client('textract')

    # Call analyze_document API (PDFs are supported if within size limits)
    response = client.analyze_document(
        Document={'Bytes': pdf_bytes},
        FeatureTypes=['TABLES']
    )

    # Optionally, print all the blocks for debugging
    # pprint(response['Blocks'])

    blocks = response['Blocks']
    blocks_map = {}
    table_blocks = []
    for block in blocks:
        blocks_map[block['Id']] = block
        if block['BlockType'] == "TABLE":
            table_blocks.append(block)

    if not table_blocks:
        return "<b>No table found in the document.</b>"

    csv_output = ''
    for index, table in enumerate(table_blocks, start=1):
        csv_output += generate_table_csv(table, blocks_map, index)
        csv_output += "\n"
    return csv_output


def main(file_name):
    # Get CSV output from the PDF file
    table_csv = get_table_csv_results(file_name)

    # Write the CSV output to a file
    output_file = 'output.csv'
    with open(output_file, "w", encoding='utf-8') as fout:
        fout.write(table_csv)

    # Print a confirmation and the CSV output
    print('CSV OUTPUT FILE:', output_file)
    print('\nExtracted CSV Content:\n')
    print(table_csv)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python script.py <PDF file>")
        sys.exit(1)
    main(sys.argv[1])
