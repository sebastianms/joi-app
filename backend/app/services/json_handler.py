import json
import os
import shutil
import uuid
from pathlib import Path
from typing import Tuple

class JsonFileError(Exception):
    """Excepción base para errores relacionados con la gestión de JSON."""
    pass

class FileTooLargeError(JsonFileError):
    """El archivo supera el límite de tamaño permitido."""
    pass

class InvalidJsonError(JsonFileError):
    """El archivo no contiene JSON válido."""
    pass

class JsonFileService:
    """
    Servicio de dominio para manejar, validar y almacenar archivos JSON subidos.
    Sigue SRP: Solo se encarga de procesar un archivo físico, asegurar sus 
    restricciones y guardarlo de manera segura.
    """
    
    MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB limit
    
    def __init__(self, upload_dir: str = "/app/data/uploads"):
        self.upload_dir = Path(upload_dir)
        self._ensure_upload_dir()

    def _ensure_upload_dir(self):
        """Crea el directorio de destino si no existe (con permisos genéricos)."""
        if not self.upload_dir.exists():
            try:
                self.upload_dir.mkdir(parents=True, exist_ok=True)
            except PermissionError:
                # Si falla por permisos (ej. no estamos en docker o data/ es de root), 
                # fallback seguro a temporal
                import tempfile
                self.upload_dir = Path(tempfile.gettempdir()) / "joi_uploads"
                self.upload_dir.mkdir(parents=True, exist_ok=True)

    async def save_and_validate(self, file_content: bytes, filename: str) -> Tuple[str, dict]:
        """
        Valida el tamaño y formato del JSON, luego lo guarda.
        
        Args:
            file_content: El binario completo del archivo subido.
            filename: Nombre original del archivo (usado para extensión referencial).
            
        Returns:
            Tuple[str, dict]: La ruta final donde se guardó el archivo y el schema/datos extraídos si corresponde.
            
        Raises:
            FileTooLargeError: Si pesa > 10MB
            InvalidJsonError: Si no es un JSON parseable
        """
        if len(file_content) > self.MAX_FILE_SIZE_BYTES:
            raise FileTooLargeError(f"El archivo excede el límite de 10 MB.")
            
        try:
            # Validamos que el contenido sea realmente un JSON
            parsed_data = json.loads(file_content.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            raise InvalidJsonError(f"Archivo JSON inválido o malformado: {str(e)}")

        # Generamos un nombre seguro y único
        safe_filename = f"{uuid.uuid4().hex}_{filename}"
        file_path = self.upload_dir / safe_filename
        
        # Guardamos a disco
        # Usamos I/O bloqueante pero al estar el buffer en memoria es rápido,
        # en alto rendimiento usaríamos aiofiles, pero para este MVP es suficiente
        with open(file_path, "wb") as f:
            f.write(file_content)
            
        return str(file_path), parsed_data
