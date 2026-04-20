import json
import pytest
from app.services.json_handler import (
    JsonFileService, 
    FileTooLargeError, 
    InvalidJsonError
)

@pytest.fixture
def json_service(tmp_path):
    # Inyectar una ruta temporal segura que no requiera root
    return JsonFileService(upload_dir=str(tmp_path / "uploads"))

@pytest.mark.asyncio
async def test_save_and_validate_success(json_service):
    """Prueba que un JSON válido se guarda correctamente y retorna su data."""
    valid_data = {"key": "value"}
    content = json.dumps(valid_data).encode("utf-8")
    
    file_path, parsed = await json_service.save_and_validate(content, "test.json")
    
    assert "test.json" in file_path
    assert parsed == valid_data

@pytest.mark.asyncio
async def test_save_and_validate_exceeds_size(json_service):
    """Prueba que un archivo que supera 10MB levanta FileTooLargeError."""
    # Simular 10MB + 1 byte
    large_content = b" " * (JsonFileService.MAX_FILE_SIZE_BYTES + 1)
    
    with pytest.raises(FileTooLargeError):
        await json_service.save_and_validate(large_content, "large.json")

@pytest.mark.asyncio
async def test_save_and_validate_invalid_json(json_service):
    """Prueba que un archivo de texto plano (no-json) levanta InvalidJsonError."""
    invalid_content = b"esto no es json: verdadero"
    
    with pytest.raises(InvalidJsonError):
        await json_service.save_and_validate(invalid_content, "bad.json")
