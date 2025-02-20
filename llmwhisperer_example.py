import sys

from unstract.llmwhisperer import LLMWhispererClientV2
from unstract.llmwhisperer.client_v2 import LLMWhispererClientException


# Define a function to process a document
def process_document(file_path):
    # Provide the base URL and API key explicitly
    client = LLMWhispererClientV2(base_url="https://llmwhisperer-api.us-central.unstract.com/api/v2",
                                  api_key="")

    try:
        # Process the document
        result = client.whisper(
                    file_path=file_path,
                    wait_for_completion=True,
                    wait_timeout=200,
                )
        # Print the extracted text
        print(result['extraction']['result_text'])
    except LLMWhispererClientException as e:
        print(e)


# Main function
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python script.py <PDF file>")
        sys.exit(1)
    process_document(sys.argv[1])
