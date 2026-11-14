from engine.classifier import classify_document
from engine.router import route_document
from engine.pdf_utils import pdf_to_images
import json
import os


path = input("Image or PDF: ").strip().strip('"')

if not os.path.isfile(path):
    print(f"\nError: File not found: {path}")
    raise SystemExit(1)


# ---------------- PDF ----------------

if path.lower().endswith(".pdf"):

    pages = pdf_to_images(path)

    all_results = []

    for i, page in enumerate(pages):

        print(f"\n================ PAGE {i + 1} ================\n")

        classification = classify_document(page)

        print("Classification:")
        print(json.dumps(classification, indent=4, ensure_ascii=False))

        result = route_document(
            classification.get("document_type", "Unknown"),
            page,
            document_subtype=classification.get("document_subtype"),
            routing_action=classification.get("routing_action"),
        )

        print("\nParsed:")
        print(json.dumps(result, indent=4, ensure_ascii=False))

        all_results.append(result)

    print("\n================ FINAL PDF RESULT ================\n")
    print(json.dumps(all_results, indent=4, ensure_ascii=False))


# ---------------- IMAGE ----------------

else:

    classification = classify_document(path)

    print("\nClassification:")
    print(json.dumps(classification, indent=4, ensure_ascii=False))

    result = route_document(
        classification.get("document_type", "Unknown"),
        path,
        document_subtype=classification.get("document_subtype"),
        routing_action=classification.get("routing_action"),
    )

    print("\nParsed:")
    print(json.dumps(result, indent=4, ensure_ascii=False))