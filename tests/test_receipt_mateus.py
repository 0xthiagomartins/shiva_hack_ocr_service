"""
Test case: cupom Mateus Supermercados — 11 itens, total R$ 39,65.
Valida: quantidade de itens criados, status processado e persistência no banco.
"""
import pytest
from fastapi.testclient import TestClient

from app.db import (
    STATUS_PROCESSADO,
    count_items_by_receipt,
    get_receipt_total,
    get_status,
    insert_receipt_data,
    set_status,
)
from app.main import app

# User criado no conftest (FK Receipt -> user.id)
TEST_USER_ID = "test-user-id"

# Payload do cupom Mateus (11 itens) — totais após descontos, soma = 39.65
MATEUS_RECEIPT_ITEMS = {
    "items": [
        {"description": "F MELAO AMARELO KG", "quantity": 2.345, "unit_price": 4.99, "total_value": 4.67},
        {"description": "V PEPINO KG", "quantity": 1.015, "unit_price": 5.49, "total_value": 1.01},
        {"description": "QUEIJO MUSS FAT LA PAULINA 150G", "quantity": 1.0, "unit_price": 6.90, "total_value": 5.99},
        {"description": "V CHEIRO VERDE MATEUS A UN", "quantity": 2.0, "unit_price": 2.49, "total_value": 1.98},
        {"description": "LEITE L VIDA ITALAC S-D CVAD 1L", "quantity": 1.0, "unit_price": 5.99, "total_value": 3.99},
        {"description": "CAFE NESCAFE SOLUV TRADICAO SH 40G", "quantity": 2.0, "unit_price": 6.39, "total_value": 5.98},
        {"description": "AVEIA NESTLE FLOCOS 170G", "quantity": 2.0, "unit_price": 4.99, "total_value": 5.98},
        {"description": "FEIJAO PRETO TIA DORA 1KG", "quantity": 1.0, "unit_price": 6.99, "total_value": 4.99},
        {"description": "MAC RICOSA ESPAGUETE COMUM 400G", "quantity": 2.0, "unit_price": 2.59, "total_value": 2.98},
        {"description": "ESP BRILHUS MUSO UN", "quantity": 1.0, "unit_price": 0.69, "total_value": 0.69},
        {"description": "DETERG DULAGO MACA 500ML", "quantity": 1.0, "unit_price": 1.39, "total_value": 1.39},
    ]
}
EXPECTED_ITEM_COUNT = 11
EXPECTED_TOTAL_AMOUNT = 39.65

client = TestClient(app)

MINIMAL_JPEG_B64 = "/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAv/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBEQACEQADAPEA/9k="


@pytest.fixture
def mock_pipeline_mateus(monkeypatch):
    """Simula pipeline: insere os 11 itens do cupom Mateus e marca como processado."""
    def run_pipeline_mateus(process_id: str, user_id: str, image_b64: str) -> None:
        insert_receipt_data(process_id, user_id, MATEUS_RECEIPT_ITEMS)
        set_status(process_id, STATUS_PROCESSADO)
    monkeypatch.setattr("app.main.run_pipeline", run_pipeline_mateus)


def test_mateus_receipt_creates_11_items_processado_and_persists(mock_pipeline_mateus):
    """
    Case: cupom Mateus Supermercados (11 itens, total R$ 39,65).
    - POST /process dispara o pipeline (mockado com payload Mateus).
    - Valida: status final = processado.
    - Valida: quantidade de registros Item no banco = 11.
    - Valida: Receipt.total_amount = 39,65 (cadastrado no banco).
    """
    process_id = "mateus-receipt-test-1"

    r = client.post(
        "/process",
        json={
            "process_id": process_id,
            "user_id": TEST_USER_ID,
            "image_b64": MINIMAL_JPEG_B64,
        },
    )
    assert r.status_code == 200
    assert r.json()["process_id"] == process_id
    assert r.json()["status"] == "em processamento"

    # Background task (mock) roda após o response; consulta status
    status = get_status(process_id)
    assert status is not None
    assert status["status"] == STATUS_PROCESSADO, (
        f"Esperado status 'processado'; obtido: {status.get('status')}; erro: {status.get('error_message')}"
    )

    # Quantidade esperada de itens no banco
    item_count = count_items_by_receipt(process_id)
    assert item_count == EXPECTED_ITEM_COUNT, (
        f"Esperado {EXPECTED_ITEM_COUNT} itens; cadastrados: {item_count}"
    )

    # Total da nota cadastrado no banco
    total = get_receipt_total(process_id)
    assert total is not None
    assert abs(total - EXPECTED_TOTAL_AMOUNT) < 0.01, (
        f"Esperado total R$ {EXPECTED_TOTAL_AMOUNT}; cadastrado: R$ {total}"
    )
