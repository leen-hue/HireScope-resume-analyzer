import json
from datetime import datetime
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from azure_clients import get_doc_intel_client, get_language_client, get_blob_container


def extract_text(file_bytes: bytes) -> str:
    client = get_doc_intel_client()
    poller = client.begin_analyze_document(
        "prebuilt-read", body=file_bytes, content_type="application/octet-stream"
    )
    return poller.result().content


def analyze_language(text: str) -> dict:
    client = get_language_client()
    docs = [text[:5000]]

    key_phrases = client.extract_key_phrases(docs)[0].key_phrases
    entities = [
        {"text": e.text, "category": e.category}
        for e in client.recognize_entities(docs)[0].entities
    ]
    pii = client.recognize_pii_entities(docs)
    redacted_text = pii[0].redacted_text
    sentiment = client.analyze_sentiment(docs)[0]
    language = client.detect_language(docs)[0].primary_language.name

        # Extractive summarization — works in more regions than abstractive
    poller = client.begin_extract_summary(docs)
    summary_result = poller.result()
    document_result = next(iter(summary_result))
    summary = " ".join(s.text for s in document_result.sentences)

    return {
        "key_phrases": key_phrases,
        "entities": entities,
        "redacted_text": redacted_text,
        "sentiment": sentiment.sentiment,
        "language": language,
        "summary": summary,
    }

def match_score(resume_text: str, job_description: str):
    """Local TF-IDF cosine similarity -- no Azure call, no cost."""
    if not job_description.strip():
        return None
    vectorizer = TfidfVectorizer(stop_words="english")
    vectors = vectorizer.fit_transform([resume_text, job_description])
    score = cosine_similarity(vectors[0:1], vectors[1:2])[0][0]
    return round(float(score) * 100, 1)  # as a percentage


def save_to_history(filename: str, analysis: dict, uploader: str, file_bytes: bytes = None) -> str:
    container = get_blob_container()
    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    safe_uploader = uploader.strip().lower().replace(" ", "-")

    if file_bytes is not None:
        resume_blob_name = f"resumes/{safe_uploader}/{timestamp}-{filename}"
        container.upload_blob(resume_blob_name, file_bytes, overwrite=True)
        analysis["source_resume_blob"] = resume_blob_name

    report_blob_name = f"reports/{safe_uploader}/{timestamp}-{filename}.json"
    container.upload_blob(report_blob_name, json.dumps(analysis, indent=2), overwrite=True)
    return report_blob_name


def load_history(uploader: str) -> list:
    container = get_blob_container()
    safe_uploader = uploader.strip().lower().replace(" ", "-")
    return [b.name for b in container.list_blobs(name_starts_with=f"reports/{safe_uploader}/")]
