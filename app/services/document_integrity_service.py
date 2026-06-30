"""
Serviço de integridade de documentos.

Verifica se o arquivo local existe para cada documento registrado no SQLite.
Não apaga dados, não inativa documentos automaticamente — apenas diagnostica.
"""
import os
from datetime import datetime, timezone

from app.database import get_db


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _compute_integrity(doc: dict) -> dict:
    """
    Retorna os campos de integridade para um documento sem gravar no banco.
    Regras:
      - inactive   → documento inativo (active=0)
      - remote_only → sem local_path mas tem gemini_document_name
      - missing_local_file → local_path definido mas arquivo ausente no disco
      - ok         → arquivo local presente
      - failed     → sem local_path e sem gemini_document_name
    """
    now = _now_iso()
    active = bool(doc.get("active", 1))
    local_path = doc.get("local_path")
    gemini_document_name = doc.get("gemini_document_name")

    if not active:
        return {
            "local_file_exists": 0,
            "integrity_status": "inactive",
            "integrity_message": "Documento inativo.",
            "integrity_checked_at": now,
        }

    if not local_path:
        if gemini_document_name:
            return {
                "local_file_exists": 0,
                "integrity_status": "remote_only",
                "integrity_message": (
                    "Documento sem arquivo local, apenas no índice remoto Gemini."
                ),
                "integrity_checked_at": now,
            }
        return {
            "local_file_exists": 0,
            "integrity_status": "failed",
            "integrity_message": "Documento sem local_path e sem gemini_document_name.",
            "integrity_checked_at": now,
        }

    if os.path.isfile(local_path):
        return {
            "local_file_exists": 1,
            "integrity_status": "ok",
            "integrity_message": "Arquivo local encontrado.",
            "integrity_checked_at": now,
        }

    return {
        "local_file_exists": 0,
        "integrity_status": "missing_local_file",
        "integrity_message": (
            "Arquivo local não encontrado. "
            "O registro SQLite e o índice remoto podem ainda existir."
        ),
        "integrity_checked_at": now,
    }


def _persist_integrity(conn, document_id: int, fields: dict) -> None:
    conn.execute(
        """
        UPDATE documents
        SET local_file_exists     = ?,
            integrity_status      = ?,
            integrity_message     = ?,
            integrity_checked_at  = ?
        WHERE id = ?
        """,
        (
            fields["local_file_exists"],
            fields["integrity_status"],
            fields["integrity_message"],
            fields["integrity_checked_at"],
            document_id,
        ),
    )


def check_document_integrity(document_id: int) -> dict | None:
    """
    Verifica e persiste integridade de um documento.
    Retorna o documento atualizado ou None se não encontrado.
    """
    with get_db() as conn:
        doc = conn.execute(
            """
            SELECT d.*, s.tenant_id, s.store_key, s.display_name, s.gemini_store_name
            FROM documents d
            JOIN stores s ON s.id = d.store_id
            WHERE d.id = ?
            """,
            (document_id,),
        ).fetchone()
        if not doc:
            return None

        fields = _compute_integrity(doc)
        _persist_integrity(conn, document_id, fields)
        doc = {**doc, **fields}

    return doc


def check_store_integrity(store_id: int) -> dict:
    """
    Verifica integridade de todos os documentos de uma store.
    Persiste os campos e retorna summary + items.
    """
    with get_db() as conn:
        docs = conn.execute(
            "SELECT * FROM documents WHERE store_id = ?",
            (store_id,),
        ).fetchall()

        summary = {
            "total": 0,
            "ok": 0,
            "missingLocalFile": 0,
            "inactive": 0,
            "remoteOnly": 0,
            "failed": 0,
        }
        items = []

        for doc in docs:
            fields = _compute_integrity(doc)
            _persist_integrity(conn, doc["id"], fields)

            summary["total"] += 1
            status = fields["integrity_status"]
            if status == "ok":
                summary["ok"] += 1
            elif status == "missing_local_file":
                summary["missingLocalFile"] += 1
            elif status == "inactive":
                summary["inactive"] += 1
            elif status == "remote_only":
                summary["remoteOnly"] += 1
            else:
                summary["failed"] += 1

            items.append({
                "id": doc["id"],
                "originalFilename": doc["original_filename"],
                "active": bool(doc.get("active", 1)),
                "localFileExists": bool(fields["local_file_exists"]),
                "integrityStatus": status,
                "integrityMessage": fields["integrity_message"],
            })

    return {"summary": summary, "items": items}


def mark_missing_files_for_store(store_id: int) -> dict:
    """Alias de check_store_integrity — apenas diagnostica, não inativa."""
    return check_store_integrity(store_id)
