import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.core.security import current_user, create_access_token, hash_password, verify_password
from app.models import User, Document, DocumentChunk, Conversation, Message
from app.schemas import AuthInput, TokenOut, UserOut, DocumentOut, AskInput, CompareInput, SearchInput
from app.services.documents import extract_upload, split_chunks
from app.services.gemini import GeminiService
from app.services.rag import owned_documents, retrieve, grounded_answer, source_payload

router = APIRouter(prefix="/api")


def token_response(user):
    return TokenOut(access_token=create_access_token(str(user.id)), user=UserOut.model_validate(user))


@router.post("/auth/register", response_model=TokenOut, status_code=201)
def register(body: AuthInput, db: Session = Depends(get_db)):
    email = body.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "An account with this email already exists")
    user = User(email=email, password_hash=hash_password(body.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return token_response(user)


@router.post("/auth/login", response_model=TokenOut)
def login(body: AuthInput, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Email or password is incorrect")
    return token_response(user)


@router.get("/auth/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return user


@router.get("/documents", response_model=list[DocumentOut])
def list_documents(db: Session = Depends(get_db), user: User = Depends(current_user)):
    return list(db.scalars(select(Document).where(Document.owner_id == user.id).order_by(Document.created_at.desc())).all())


@router.post("/documents", response_model=DocumentOut, status_code=201)
async def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(current_user)):
    max_bytes = settings.max_upload_mb * 1024 * 1024
    text, page_count, raw = await extract_upload(file, max_bytes)
    service = GeminiService()
    document = Document(owner_id=user.id, filename=Path(file.filename or "document").name[:255], content_type=file.content_type or "application/octet-stream", size_bytes=len(raw), page_count=page_count, extracted_text=text)
    try:
        db.add(document)
        db.flush()
        for index, content in enumerate(split_chunks(text)):
            embedding = await service.embed(content)
            db.add(DocumentChunk(document_id=document.id, chunk_index=index, page_number=None, content=content, embedding=embedding))
        db.commit()
        db.refresh(document)
    except Exception:
        db.rollback()
        raise
    return document


@router.get("/documents/{document_id}", response_model=DocumentOut)
def get_document(document_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(current_user)):
    document = db.scalar(select(Document).where(Document.id == document_id, Document.owner_id == user.id))
    if not document:
        raise HTTPException(404, "Document not found")
    return document


@router.delete("/documents/{document_id}", status_code=204)
def delete_document(document_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(current_user)):
    document = db.scalar(select(Document).where(Document.id == document_id, Document.owner_id == user.id))
    if not document:
        raise HTTPException(404, "Document not found")
    db.delete(document)
    db.commit()


@router.get("/documents/{document_id}/text")
def document_text(document_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(current_user)):
    document = db.scalar(select(Document).where(Document.id == document_id, Document.owner_id == user.id))
    if not document:
        raise HTTPException(404, "Document not found")
    return {"id": document.id, "filename": document.filename, "text": document.extracted_text}


@router.post("/documents/{document_id}/summary")
async def summarize(document_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(current_user)):
    document = db.scalar(select(Document).where(Document.id == document_id, Document.owner_id == user.id))
    if not document:
        raise HTTPException(404, "Document not found")
    summary = await GeminiService().generate("Summarize the following document accurately. Preserve important facts and clearly flag uncertainty.\n\n" + document.extracted_text[:50000])
    return {"summary": summary}


@router.post("/search")
async def semantic_search(body: SearchInput, db: Session = Depends(get_db), user: User = Depends(current_user)):
    if body.document_ids is not None:
        owned_documents(db, user.id, body.document_ids)
    results = await retrieve(db, user.id, body.query, body.document_ids, body.limit)
    return {"results": [{**source_payload([r])[0], "content": r["chunk"].content, "similarity": max(0, 1-r["distance"])} for r in results]}


@router.post("/compare")
async def compare(body: CompareInput, db: Session = Depends(get_db), user: User = Depends(current_user)):
    docs = owned_documents(db, user.id, body.document_ids)
    materials = "\n\n".join(f"DOCUMENT {d.filename}:\n{d.extracted_text[:20000]}" for d in docs)
    answer = await GeminiService().generate("Compare only the supplied documents. State similarities and differences and cite document names. Say when evidence is absent.\n\n" + body.prompt + "\n\n" + materials)
    return {"answer": answer, "documents": [{"id": d.id, "filename": d.filename} for d in docs]}


@router.post("/conversations", status_code=201)
def create_conversation(db: Session = Depends(get_db), user: User = Depends(current_user)):
    conversation = Conversation(owner_id=user.id)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return {"id": conversation.id, "title": conversation.title, "created_at": conversation.created_at}


@router.get("/conversations")
def list_conversations(db: Session = Depends(get_db), user: User = Depends(current_user)):
    rows = db.scalars(select(Conversation).where(Conversation.owner_id == user.id).order_by(Conversation.created_at.desc())).all()
    return [{"id": r.id, "title": r.title, "created_at": r.created_at} for r in rows]


@router.get("/conversations/{conversation_id}/messages")
def list_messages(conversation_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(current_user)):
    convo = db.scalar(select(Conversation).where(Conversation.id == conversation_id, Conversation.owner_id == user.id))
    if not convo:
        raise HTTPException(404, "Conversation not found")
    return [{"id": m.id, "role": m.role, "content": m.content, "sources": m.sources, "created_at": m.created_at} for m in convo.messages]


@router.post("/conversations/{conversation_id}/messages")
async def ask(conversation_id: uuid.UUID, body: AskInput, db: Session = Depends(get_db), user: User = Depends(current_user)):
    convo = db.scalar(select(Conversation).where(Conversation.id == conversation_id, Conversation.owner_id == user.id))
    if not convo:
        raise HTTPException(404, "Conversation not found")
    if body.document_ids is not None:
        owned_documents(db, user.id, body.document_ids)
    results = await retrieve(db, user.id, body.question, body.document_ids, 8)
    answer = await grounded_answer(body.question, results)
    sources = source_payload(results)
    try:
        db.add(Message(conversation_id=convo.id, role="user", content=body.question))
        db.add(Message(conversation_id=convo.id, role="assistant", content=answer, sources=sources))
        if convo.title == "New conversation":
            convo.title = body.question[:190]
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {"answer": answer, "sources": sources}
