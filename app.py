from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import datetime
from pathlib import Path

import streamlit as st

from engine.classifier import classify_document
from engine.router import route_document
from engine.pdf_utils import pdf_to_images


st.set_page_config(
    page_title="GoMeds AI Engine",
    page_icon="G",
    layout="wide",
)

st.title("GoMeds AI Engine")
st.caption("Healthcare document extraction · Local Windows app")

st.info(
    "Privacy note: this interface runs on your computer, but the AI model "
    "processes document images through the NVIDIA API configured in your "
    ".env file. Use test documents until patient-data handling and compliance "
    "have been reviewed."
)

st.markdown("### 1. Upload a document")
uploaded_file = st.file_uploader(
    "Choose a PDF or image",
    type=["pdf", "png", "jpg", "jpeg", "webp"],
    accept_multiple_files=False,
    help="Supported formats: PDF, PNG, JPG, JPEG, WEBP.",
)

file_signature = None
if uploaded_file is not None:
    file_bytes = uploaded_file.getvalue()
    file_signature = hashlib.sha256(file_bytes).hexdigest()

    if uploaded_file.type and uploaded_file.type.startswith("image/"):
        st.image(file_bytes, caption=uploaded_file.name, width=600)
    else:
        st.caption(f"Selected file: {uploaded_file.name} ({len(file_bytes):,} bytes)")

st.markdown("### 2. Extract information")
process_clicked = st.button(
    "Process document",
    type="primary",
    disabled=uploaded_file is None,
)

if process_clicked and uploaded_file is not None:
    results = []
    suffix = Path(uploaded_file.name).suffix.lower()
    uploads_dir = Path("uploads")
    uploads_dir.mkdir(parents=True, exist_ok=True)

    safe_name = re.sub(
        r"[^A-Za-z0-9._-]+",
        "_",
        Path(uploaded_file.name).name,
    ).strip("._") or "uploaded_document"
    saved_path = uploads_dir / f"{uuid.uuid4().hex[:8]}_{safe_name}"

    try:
        saved_path.write_bytes(file_bytes)

        with st.spinner("Processing the document. This may take a little while..."):
            if suffix == ".pdf":
                pages = pdf_to_images(str(saved_path))
                if not pages:
                    raise RuntimeError(
                        "No pages were produced from this PDF. Check that the PDF opens correctly."
                    )

                progress = st.progress(0, text="Processing PDF pages...")
                total_pages = len(pages)

                for index, page_path in enumerate(pages, start=1):
                    try:
                        classification = classify_document(str(page_path))
                        parsed = route_document(
                            classification.get("document_type", "Unknown"),
                            str(page_path),
                            document_subtype=classification.get("document_subtype"),
                            routing_action=classification.get("routing_action"),
                        )
                        results.append(
                            {
                                "page": index,
                                "classification": classification,
                                "parsed": parsed,
                            }
                        )
                    except Exception as exc:
                        results.append(
                            {
                                "page": index,
                                "error": str(exc),
                            }
                        )
                    progress.progress(
                        index / total_pages,
                        text=f"Processed page {index} of {total_pages}",
                    )
                progress.empty()
            else:
                classification = classify_document(str(saved_path))
                parsed = route_document(
                    classification.get("document_type", "Unknown"),
                    str(saved_path),
                    document_subtype=classification.get("document_subtype"),
                    routing_action=classification.get("routing_action"),
                )
                results.append(
                    {
                        "classification": classification,
                        "parsed": parsed,
                    }
                )

        st.session_state["gomeds_results"] = {
            "source_name": uploaded_file.name,
            "source_signature": file_signature,
            "saved_path": str(saved_path),
            "processed_at": datetime.now().isoformat(timespec="seconds"),
            "results": results,
        }

    except Exception as exc:
        st.error(f"Processing failed: {exc}")
        st.caption(
            "Check the Command Prompt for additional details. Your existing Python engine has not been replaced."
        )

saved_results = st.session_state.get("gomeds_results")
if (
    saved_results
    and file_signature
    and saved_results.get("source_signature") == file_signature
):
    st.markdown("---")
    st.markdown("### 3. Results")
    st.caption(
        f"File: {saved_results['source_name']} · "
        f"Processed: {saved_results['processed_at']}"
    )

    for index, item in enumerate(saved_results["results"], start=1):
        if "page" in item:
            heading = f"Page {item['page']}"
        elif item.get("classification"):
            heading = item["classification"].get("document_type", "Document")
        else:
            heading = f"Result {index}"

        with st.expander(heading, expanded=True):
            if "error" in item:
                st.error(item["error"])
                continue

            classification = item.get("classification", {})
            parsed = item.get("parsed", {})

            st.markdown("**Document classification**")
            st.json(classification)

            st.markdown("**Extracted information**")
            st.json(parsed)

            if parsed.get("review_required") or parsed.get("fields_needing_review"):
                st.warning(
                    "Some information requires manual verification. Do not treat uncertain extraction as verified medical information."
                )

    export_data = {
        "source_file": saved_results["source_name"],
        "processed_at": saved_results["processed_at"],
        "results": saved_results["results"],
    }
    json_bytes = json.dumps(
        export_data,
        indent=2,
        ensure_ascii=False,
    ).encode("utf-8")

    st.download_button(
        "Download results as JSON",
        data=json_bytes,
        file_name=f"gomeds_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        mime="application/json",
        type="primary",
    )

    st.caption(
        f"Local uploaded copy: {saved_results['saved_path']}. "
        "The file remains in the uploads folder until you delete it."
    )
elif saved_results and uploaded_file is not None:
    st.caption("A different file is selected. Click Process document to extract its results.")

st.markdown("---")
st.caption(
    "Review medicine names, strengths, dosage schedules, lab values and units before relying on the extracted data."
)
